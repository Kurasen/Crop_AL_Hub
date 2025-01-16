from flask import Blueprint, request
from app.blueprint.utils.JWT import generate_token, token_required
from flask_restx import Resource, Api, fields

# 模拟用户数据
USERS = [
    {"id": 1, "username": "test001", "password": "123123", "telephone": "1234567890", "email": "user1@example.com"},
    {"id": 2, "username": "test002", "password": "123123", "telephone": "1234567891", "email": "user2@example.com"},
    {"id": 3, "username": "test003", "password": "123123", "telephone": "1234567892", "email": "user3@example.com"},
]

# 创建 Blueprint 和 URL 前缀
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
# 定义 Flask-RESTX 的 API 文档对象
api = Api(version='1.0', title='Flask Login API', description='Login functionality with JWT')
# 定义命名空间
auth_ns = api.namespace('auth', description='Operations related to auth')

# 定义 Swagger 接口参数模型
login_model = api.model('Login', {
    'login_identifier': fields.String(required=True, description='Username, telephone, or email for login'),
    'login_type': fields.String(required=True, description='The type of login: username, telephone, or email'),
    'password': fields.String(required=True, description='The password for login')
})


# 注册模型
api.models['Login'] = login_model


# 登录功能：使用 Flask-RESTX 的 Resource 类来处理 POST 请求
@auth_ns.route('/login')  # 这里是直接定义接口路由
class LoginResource(Resource):
    @api.doc(description='Login and get a JWT token')
    @api.expect(login_model)  # 绑定 Swagger 文档模型
    def post(self):
        # 从请求中获取数据
        data = request.get_json()
        login_identifier = data['login_identifier']
        login_type = data['login_type']
        password = data['password']

        if not data or 'login_identifier' not in data or 'password' not in data or 'login_type' not in data:
            return {"message": "Missing login identifier, password, or login type"}, 400

        # 模拟数据验证
        if login_type == "username":
            user = next((u for u in USERS if u["username"] == login_identifier), None)
        elif login_type == "telephone":
            user = next((u for u in USERS if u["telephone"] == login_identifier), None)
        elif login_type == "email":
            user = next((u for u in USERS if u["email"] == login_identifier), None)
        else:
            return {"message": "Invalid login type"}, 400

        # # 根据 login_type 查询对应字段
        # if login_type == 'username':
        #     user = UserModel.query.filter_by(username=login_identifier).first()
        # elif login_type == 'telephone':
        #     user = UserModel.query.filter_by(telephone=login_identifier).first()
        # elif login_type == 'email':
        #     user = UserModel.query.filter_by(email=login_identifier).first()
        # else:
        #     return {"message": "Invalid login type"}, 400  # 如果传递的 login_type 不合法
        #
        # if not user or not check_password_hash(user.password, password):
        #     return {"message": "Invalid username or password"}, 401
        #
        # # 生成 JWT
        # token = generate_token(user.id, user.username)
        # return {"message": "Login successful", "token": token}, 200
        # # 可选：添加一个 GET 方法供调试或说明用途

        # 模拟验证用户和密码
        if not user or user["password"] != password:
            return {"message": "Invalid username, telephone, email, or password"}, 401

        # 生成 JWT Token
        token = generate_token(user["id"], user["username"])  # 使用 user["id"] 和 user["username"]
        return {"message": "Login successful", "token": token}, 200

    def get(self):
        return {"message": "Use POST method to login"}, 200


# 受保护接口：需要使用 JWT 认证
@auth_ns.route('/protected')
class ProtectedRoute(Resource):
    @api.doc(description='Protected route, requires JWT token')
    @token_required  # 使用装饰器，确保用户已认证
    def get(self, current_user):
        # 输出 current_user 调试信息
        print(f"current_user: {current_user}, type: {type(current_user)}")

        # 确保 current_user 是字典类型并包含 'username' 键
        if not isinstance(current_user, dict):
            return {"message": "Invalid user data"}, 400
        return {"message": f"Hello, {current_user['username']}!"}, 200
