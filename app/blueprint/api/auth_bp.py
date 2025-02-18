
from flask import request, Blueprint
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError

from app.blueprint.utils.JSONEncoder import create_json_response
from app.blueprint.utils.JWT import token_required, add_to_blacklist, get_jwt_identity, verify_token
from app.exception.errors import ValidationError, DatabaseError, AuthenticationError, logger
from app.repositories.Token.token_repo import TokenRepository
from app.services.Auth.auth_service import AuthService
from app.services.Auth.verify_code_service import VerificationCodeService
from app.services.Token.token_service import TokenService

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    用户注册 API
    """
    if not request.is_json:
        raise ValidationError("Request must be JSON")

    # 获取请求的数据
    data = request.get_json()

    # 通过服务层进行注册处理
    response, status = AuthService.register(data)

    # 使用 create_json_response 返回 JSON 响应
    return create_json_response(response, status)


@auth_bp.route('/login', methods=['POST'])
def login():
    if not request.is_json:
        raise ValidationError("Request must be JSON")
    data = request.get_json()

    try:
        response, status = AuthService.login(data)
        return response, status
    except (IntegrityError, OperationalError, SQLAlchemyError):
        raise DatabaseError("Database error occurred. Please try again later.")


@auth_bp.route('/logout', methods=['POST'])
@token_required  # 使用装饰器，确保用户已认证
def post(current_user):
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
@auth_bp.route('/protected', methods=['GET'])
@token_required  # 使用装饰器，确保用户已认证
def protected_route(current_user):
    """受保护接口"""
    if not isinstance(current_user, dict) or 'username' not in current_user:
        raise ValidationError("Invalid user data")
    return {"message": f"Hello, {current_user['username']}!"}, 200


@auth_bp.route('/refresh_token', methods=['POST'])
def refresh_token():
    """刷新 Token"""

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
        response, status = TokenService.refresh_token(token)
        return response, status
    except AuthenticationError as e:
        # 记录刷新 Token 失败的日志
        logger.error(f"Token refresh failed: {str(e)}")
        raise e


@auth_bp.route('/generate_code', methods=['POST'])
def generate_code():
    """
    生成验证码并发送给用户（通过手机号或邮箱）
    """
    data = request.get_json()
    login_type = data.get('login_type')  # 'telephone' 或 'email'
    login_identifier = data.get('login_identifier')

    if not login_type or not login_identifier:
        raise ValidationError("Missing 'login_type' or 'login_identifier'")

    if login_type not in ['telephone', 'email']:
        raise ValidationError("Invalid 'login_type'. Should be 'telephone' or 'email'.")

    # 调用 AuthService 生成验证码
    code = VerificationCodeService.generate_verification_code(login_type, login_identifier)

    response_data = {
        "message": "Verification code sent successfully.",
        "code": code
    }

    return create_json_response(response_data, status_code=200)

