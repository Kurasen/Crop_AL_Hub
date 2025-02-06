import re

from werkzeug.security import check_password_hash

from app.blueprint.utils.JWT import generate_token
from app.blueprint.utils.auth_utils import verify_password
from app.repositories.User.auth_repo import AuthRepository


class AuthService:

    @staticmethod
    def login(data):
        """
        登录服务：处理用户登录并生成 Token。
        """
        login_identifier = data['login_identifier']
        login_type = data['login_type']
        password = data['password']

        # # Step 1: 校验输入格式
        # format_check = AuthService.validate_username_format(login_type, login_identifier)
        # if format_check:
        #     return format_check  # 如果格式不正确，返回错误信息
        #
        # # Step 2: 校验密码格式
        # is_valid, message = AuthService.validate_password_format(password)
        # if not is_valid:
        #     return {"message": message}, 400  # 如果密码不符合要求，返回错误信息

        # Step 3: 检查登录失败次数
        if not AuthRepository.check_login_attempts(login_identifier):
            return {"message": "Too many login attempts. Please try again later."}, 429

        # Step 4: 使用 Redis 锁来防止并发请求
        redis_client = AuthRepository.get_redis_client()
        lock_key = f"lock:{login_identifier}"
        lock = redis_client.set(lock_key, 'locked', nx=True, ex=5)  # 5 秒锁
        if not lock:
            return {"message": "Too many users, please try again later."}, 429

        try:
            # Step 5: 验证用户身份
            user = AuthRepository.get_user_by_identifier(login_identifier, login_type)
            if not user or not verify_password(user, password):  # 密码校验
                AuthRepository.increment_login_attempts(login_identifier)
                return {"message": "Invalid username or password"}, 401

            # Step 6: 登录成功，重置登录次数，生成 Token
            AuthRepository.reset_login_attempts(login_identifier)
            token = generate_token(user.id, user.username)
            return {"message": "Login successful", "token": token}, 200
        finally:
            redis_client.delete(lock_key)

    @staticmethod
    def check_password(user, password):
        """验证密码"""
        return check_password_hash(user.password, password)

    @staticmethod
    def authenticate_user(login_identifier, login_type, password):
        """验证用户身份"""
        user = AuthRepository.get_user_by_identifier(login_identifier, login_type)
        if user and verify_password(user, password):
            return user, None
        return None, "Invalid username or password"

    @staticmethod
    def generate_jwt(user):
        """生成 JWT Token"""
        return generate_token(user.id, user.username)

    # 验证输入格式
    @staticmethod
    def validate_username_format(login_type, login_identifier):
        """验证用户名、电话或邮箱格式"""
        patterns = {
            'username': r'^[a-zA-Z0-9_]{3,20}$',
            'telephone': r'^\+?[0-9]{10,15}$',
            'email': r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        }
        if not re.match(patterns.get(login_type, ""), login_identifier):
            return {"message": f"Invalid {login_type} format"}, 400
        return None

    # 验证密码格式
    @staticmethod
    def validate_password_format(password):
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        if not re.search(r'[A-Z]', password):  # 至少一个大写字母
            return False, "Password must contain at least one uppercase letter"
        if not re.search(r'[a-z]', password):  # 至少一个小写字母
            return False, "Password must contain at least one lowercase letter"
        if not re.search(r'[0-9]', password):  # 至少一个数字
            return False, "Password must contain at least one number"
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):  # 至少一个特殊字符
            return False, "Password must contain at least one special character"
        return True, ""

    @staticmethod
    def refresh_token(token):
        """
        刷新 Token，调用 AuthRepository 的 refresh_token 方法。
        :param token: 旧的 JWT Token
        :return: 新的 Access Token 或错误信息
        """
        return AuthRepository.refresh_token(token)