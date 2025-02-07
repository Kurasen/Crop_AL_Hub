
from flask import request
from flask_restx import Resource, fields, Namespace
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError

from app.blueprint.utils.JWT import token_required
from app.exception.errors import ValidationError, DatabaseError
from app.repositories.Token.token_repo import TokenRepository
from app.services.auth_service import AuthService

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
        """用户登录"""
        if not request.is_json:
            raise ValidationError("Request must be of type JSON")
        data = request.get_json()
        if not data:
            raise ValidationError("Request body must be a valid JSON")

        missing_fields = [field for field in ['login_identifier', 'password', 'login_type'] if not data.get(field)]
        if missing_fields:
            raise ValidationError(f"Missing fields: {', '.join(missing_fields)}")

        try:
            # 将数据传递给 AuthService 处理
            response, status = AuthService.login(data)
            return response, status

        except (IntegrityError, OperationalError, SQLAlchemyError):
            raise DatabaseError("Database error occurred. Please try again later.")

    def get(self):
        return {"message": "Use POST method to login"}, 200


@auth_ns.route('/logout')
class LogoutResource(Resource):
    @auth_ns.doc(description='Logout and invalidate JWT token',
                 params={'Authorization': 'Bearer <your_token>'})#为了方便在swagger上测试
    @token_required  # 使用装饰器，确保用户已认证
    def post(self, current_user):
        """登出功能"""
        # 获取当前用户的 ID
        user_id = current_user['user_id']

        # 检查 token 是否存在于 Redis 中
        if not TokenRepository.token_exists_in_redis(user_id):
            raise ValidationError("Token not found or already logged out.")

        # 删除 Redis 中存储的 Token
        TokenRepository.delete_user_token(user_id)

        # 返回成功消息
        return {"message": "Logout successful"}, 200


# 受保护接口：需要使用 JWT 认证
@auth_ns.route('/protected')
class ProtectedRoute(Resource):
    @auth_ns.doc(description='Protected route, requires JWT token')
    @token_required  # 使用装饰器，确保用户已认证
    def get(self, current_user):
        """受保护接口"""
        if not isinstance(current_user, dict) or 'username' not in current_user:
            raise ValidationError("Invalid user data")
        return {"message": f"Hello, {current_user['username']}!"}, 200


@auth_ns.route('/refresh')
class RefreshTokenResource(Resource):
    @auth_ns.doc(description='Refresh the expired JWT token')
    def post(self):
        """刷新 Token"""
        token = request.headers.get('Authorization')
        if not token:
            raise ValidationError("Token is missing")

        # 处理 Bearer 头
        if token.startswith('Bearer '):
            token = token[len('Bearer '):]

        return AuthService.refresh_token(token)


