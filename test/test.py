import unittest
import requests

BASE_URL = "http://127.0.0.1:5000/auth"

class TestAuthAPI(unittest.TestCase):

    def setUp(self):
        """在测试开始前运行，用于初始化测试数据"""
        # 定义测试用户数据
        self.valid_user = {
            "login_identifier": "test001",
            "login_type": "username",
            "password": "123123"
        }
        self.invalid_user = {
            "login_identifier": "1234567891",
            "login_type": "telephone",
            "password": "123123"
        }

    def test_login_success(self):
        """测试登录成功"""
        response = requests.post(f"{BASE_URL}/login", json=self.valid_user)
        self.assertEqual(response.status_code, 200)
        self.assertIn("token", response.json())
        self.assertEqual(response.json()["message"], "Login successful")

    def test_login_invalid_user(self):
        """测试无效用户登录"""
        response = requests.post(f"{BASE_URL}/login", json=self.invalid_user)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["message"], "Invalid username or password")

    def test_login_missing_fields(self):
        """测试缺少字段或字段为空的请求"""
        test_cases = [
            ({"login_identifier": "test001", "password": "123123"}, "login_type"),
            ({"login_type": "username", "password": "123123"}, "login_identifier"),
            ({"login_identifier": "test001", "login_type": "username"}, "password"),
            ({"login_identifier": "test001", "login_type": "username", "password": ""}, "password")
        ]
        for data, missing_field in test_cases:
            response = requests.post(f"{BASE_URL}/login", json=data)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()["message"], f"Missing or empty fields: {missing_field}")

    def test_login_invalid_login_type(self):
        """测试不支持的 login_type"""
        invalid_type_data = {
            "login_identifier": "test001",
            "login_type": "unknown",
            "password": "123123"
        }
        response = requests.post(f"{BASE_URL}/login", json=invalid_type_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "Invalid login type")

    def test_protected_route_without_token(self):
        """测试访问受保护路由时未提供 token"""
        response = requests.get(f"{BASE_URL}/protected")
        self.assertEqual(response.status_code, 401)  # 假设 token_required 装饰器返回 401

    def test_protected_route_with_token(self):
        # 登录获取 JWT token
        response = requests.post(f"{BASE_URL}/auth/login", json=self.valid_user)
        self.assertEqual(response.status_code, 200)
        token = response.json()["token"]

        # 使用 token 访问受保护的路由
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/auth/protected", headers=headers)
        self.assertEqual(response.status_code, 200)

        # 动态验证返回消息
        expected_username = self.valid_user["login_identifier"]
        self.assertIn(f"Hello, {expected_username}!", response.json()["message"])

if __name__ == "__main__":
    unittest.main()
