import redis
from flask import request, current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from app.blueprint.utils.JWT import token_required
from flask_restx import Resource, Api, fields, Namespace
from app.repositories.User.auth_repo import AuthRepository
from app.repositories.User.login_attempt_repo import LoginAttemptsRepository

auth_ns = Namespace('auth', description='Operations related to auth')

# 定义 Swagger 接口参数模型
login_model = auth_ns.model('Login', {
    'login_identifier': fields.String(required=True, description='Username, telephone, or email for login'),
    'login_type': fields.String(required=True, description='The type of login: username, telephone, or email'),
    'password': fields.String(required=True, description='The password for login')
})


@auth_ns.route('/login')
class LoginResource(Resource):
    @auth_ns.doc(description='Login and get a JWT token')
    @auth_ns.expect(login_model)
    def post(self):
        try:
            if not request.is_json:
                return {"message": "Request must be of type JSON"}, 400
            data = request.get_json()
            if not data:
                return {"message": "Request body must be a valid JSON"}, 400

            missing_fields = [field for field in ['login_identifier', 'password', 'login_type'] if not data.get(field)]
            if missing_fields:
                return {"message": f"Missing fields: {', '.join(missing_fields)}"}, 400

            login_identifier = data['login_identifier']
            login_type = data['login_type']
            password = data['password']

            # Step 1: 检查登录次数限制
            if not LoginAttemptsRepository.check_login_attempts(login_identifier):
                return {"message": "Too many login attempts. Please try again later."}, 429

            # Step 2: 进行身份验证
            response, status = AuthRepository.login_user(login_identifier, login_type, password)
            return response, status

        except (IntegrityError, OperationalError, SQLAlchemyError):
            return {"message": "Database error occurred. Please try again later."}, 500

    def get(self):
        return {"message": "Use POST method to login"}, 200


# 受保护接口：需要使用 JWT 认证
@auth_ns.route('/protected')
class ProtectedRoute(Resource):
    @auth_ns.doc(description='Protected route, requires JWT token')
    @token_required  # 使用装饰器，确保用户已认证
    def get(self, current_user):
        # 输出 current_user 调试信息
        print(f"current_user: {current_user}, type: {type(current_user)}")

        # 确保 current_user 是字典类型并包含 'username' 键
        if not isinstance(current_user, dict):
            return {"message": "Invalid user data"}, 400
        return {"message": f"Hello, {current_user['username']}!"}, 200


@auth_ns.route('/refresh')
class RefreshTokenResource(Resource):
    @auth_ns.doc(description='Refresh the expired JWT token')
    def post(self):
        token = request.headers.get('Authorization')  # 从 Authorization 头中获取 Token
        if not token:
            return {"message": "Token is missing"}, 400

        # 如果 token 包含 "Bearer " 前缀，去掉它
        if token.startswith('Bearer '):
            token = token[len('Bearer '):]

        result = AuthRepository.refresh_token(token)  # 调用 AuthService 处理刷新逻辑
        return result


@auth_ns.route('/test-redis')
class TestRedisResource(Resource):
    def get(self):
        try:
            # 尝试设置和获取一个 Redis 键值对

            current_app.redis_client.set('test_key', 'Hello, Redis!')
            value = current_app.redis_client.get('test_key')
            return {"message": "Redis is working", "redis_value": value}, 200
        except redis.exceptions.ConnectionError as e:
            return {"message": "Failed to connect to Redis", "error": str(e)}, 500
