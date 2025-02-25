
from flask import request, Blueprint, current_app

from app.schemas.base import apply_rate_limit
from app.schemas.auth_schema import UserCreateSchema, UserLoginSchema, GenerateCodeSchema
from app.token.token_service import TokenService
from app.utils.json_encoder import create_json_response
from app.token.JWT import token_required, add_to_blacklist, get_jwt_identity, verify_token
from app.core.exception import ValidationError, AuthenticationError, logger
from app.token.token_repo import TokenRepository
from app.auth.auth_service import AuthService
from app.core.verify_code_service import VerificationCodeService

auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')


@auth_bp.route('/register', methods=['POST'])
@apply_rate_limit("5 per minute")
def register():
    """用户注册 API（使用Schema验证）"""
    # 使用Schema进行数据加载和验证
    validated_data = UserCreateSchema().load(request.get_json())
    # 调用服务层（传递已验证数据）
    response, status = AuthService.register(validated_data)
    return create_json_response(response, status)


@auth_bp.route('/login', methods=['POST'])
@apply_rate_limit("5 per minute")
def login():
    """
    用户登录 API
    """
    validated_data = UserLoginSchema().load(request.get_json())
    response, status = AuthService.login(validated_data)
    return create_json_response(response, status)


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
    return create_json_response("Logout successful")


# 受保护接口：需要使用 JWT 认证
@auth_bp.route('/protected', methods=['GET'])
@token_required  # 使用装饰器，确保用户已认证
def protected_route(current_user):
    """受保护接口"""
    if not isinstance(current_user, dict) or 'username' not in current_user:
        raise ValidationError("Invalid user data")
    return {"message": f"Hello, {current_user['username']}!"}, 200


@auth_bp.route('/refresh_token', methods=['POST'])
@token_required
def refresh_token(current_user):
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
        current_app.logger.error(f"Token refresh failed: {str(e)}")
        raise e

    try:
        # 验证 refresh_token 并获取新的 access_token
        response, status = TokenService.refresh_token(token)
        return response, status
    except AuthenticationError as e:
        # 记录刷新 Token 失败的日志
        current_app.logger.error(f"Token refresh failed: {str(e)}")
        raise e


@auth_bp.route('/generate_code', methods=['POST'])
@apply_rate_limit("5 per minute")
def generate_code():
    """
    生成验证码并发送给用户（通过手机号或邮箱）
    """
    validated_data = GenerateCodeSchema().load(request.get_json())
    # 调用 AuthService 生成验证码
    code = VerificationCodeService.generate_verification_code(validated_data)

    response_data = {
        "message": "Verification code sent successfully.",
        "code": code
    }

    return create_json_response(response_data, status_code=200)
