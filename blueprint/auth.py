from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash
from blueprint.utils.JWT import generate_token, token_required
from models import UserModel
from flask_restx import Resource, Api, fields

# 定义 Flask-RESTX 的 API 文档对象
api = Api(version='1.0', title='Flask Login API', description='Login functionality with JWT', doc='/swagger-ui')

# 定义 Swagger 接口参数模型
login_model = api.model('Login', {
    'username': fields.String(required=True, description='The username for login'),
    'password': fields.String(required=True, description='The password for login')
})

# 创建 Blueprint 和 URL 前缀
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# 为 auth_bp 创建 API 对象
api.init_app(auth_bp)

# 登录功能：使用 Flask-RESTX 的 Resource 类来处理 POST 请求
@api.route('/login')  # 这里是直接定义接口路由
class LoginResource(Resource):
    @api.doc(description='Login and get a JWT token')
    @api.expect(login_model)  # 绑定 Swagger 文档模型
    def post(self):
        # 从请求中获取数据
        data = request.get_json()
        username = data['username']
        password = data['password']

        if not data or 'username' not in data or 'password' not in data:
            return {"message": "Missing username or password"}, 400

        # 查询数据库中的用户
        user = UserModel.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password, password):
            return {"message": "Invalid username or password"}, 401

        # 生成 JWT
        token = generate_token(user.id, user.username)
        return {"message": "Login successful", "token": token}, 200
        # 可选：添加一个 GET 方法供调试或说明用途

    def get(self):
        return {"message": "Use POST method to login"}, 200

# 受保护接口：需要使用 JWT 认证
@api.route('/protected')
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