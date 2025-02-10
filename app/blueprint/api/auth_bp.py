from flask import request, current_app
from flask_restx import Resource, fields, Namespace
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError

from app.blueprint.utils.JWT import token_required, add_to_blacklist, get_jwt_identity, verify_token
from app.exception.errors import ValidationError, DatabaseError, AuthenticationError, logger
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
    @auth_ns.doc(description='Login and get JWT tokens')
    @auth_ns.expect(login_model)
    def post(self):
        """用户登录"""
        if not request.is_json:
            raise ValidationError("Request must be JSON")
        data = request.get_json()

        try:
            response, status = AuthService.login(data)
            return response, status
        except (IntegrityError, OperationalError, SQLAlchemyError):
            raise DatabaseError("Database error occurred. Please try again later.")


@auth_ns.route('/logout')
class LogoutResource(Resource):
    @auth_ns.doc(description='Logout and invalidate JWT token')
    @token_required  # 使用装饰器，确保用户已认证
    def post(self, current_user):
        """登出功能"""
        # 获取当前用户的 ID
        user_id = current_user['user_id']
        jti = get_jwt_identity()

        # 将 Access Token 加入黑名单
        add_to_blacklist(jti)

        # 删除 Refresh Token
        TokenRepository.delete_user_token(user_id, token_type='refresh')

        logger.info(f"User {user_id} successfully logged out.")
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


@auth_ns.route('/refresh_token')
class RefreshTokenResource(Resource):
    @auth_ns.doc(description='Refresh Access Token using Refresh Token')
    def post(self):
        """刷新 Token"""
        print(f"Request Headers: {request.headers}")  # 打印请求头信息
        token = request.headers.get('Authorization')
        if not token:
            raise ValidationError("Token is missing")
        # 处理 Bearer 头
        if token.startswith('Bearer '):
            token = token[len('Bearer '):]
        # 如果 Token 不以 "Bearer " 开头，直接使用它
        token = token.strip()  # 确保没有多余的空格

        # 验证 token 类型
        try:
            decoded = verify_token(token)
            token_type = decoded.get('token_type')

            # 如果是 access_token，则返回错误提示
            if token_type == 'access':
                raise AuthenticationError("Access token cannot be used to refresh the token. Please use a valid "
                                          "refresh token.")

        except AuthenticationError as e:
            logger.error(f"Token refresh failed: {str(e)}")
            raise e

        try:
            # 验证 refresh_token 并获取新的 access_token
            response, status = AuthService.refresh_token(token)
            return response, status
        except AuthenticationError as e:
            # 记录刷新 Token 失败的日志
            logger.error(f"Token refresh failed: {str(e)}")
            raise e
