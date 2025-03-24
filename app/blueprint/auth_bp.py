import re

from flask import request, Blueprint, g

from app.schemas.base import apply_rate_limit
from app.schemas.auth_schema import UserCreateSchema, UserLoginSchema, GenerateCodeSchema
from app.token.token_service import TokenService
from app.utils.json_encoder import create_json_response
from app.token.JWT import token_required, add_to_blacklist, get_jwt_identity, verify_token
from app.core.exception import ValidationError, AuthenticationError, logger, TokenError
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
def post():
    """登出功能"""
    user_id = g.current_user
    if not user_id:
        return create_json_response({"msg": "用户ID无效"}, status=400)

    jti = get_jwt_identity()

    # 将 Access Token 加入黑名单
    add_to_blacklist(jti)

    # 删除 Refresh Token
    TokenRepository.delete_user_token(user_id, token_type='refresh')
    logger.info(f"用户 {user_id} 成功登出")
    return create_json_response(status=204)


# 受保护接口：需要使用 JWT 认证
@auth_bp.route('/protected', methods=['GET'])
@token_required  # 使用装饰器，确保用户已认证
def protected_route():
    """受保护接口"""
    user_id = g.current_user
    if not isinstance(user_id, dict) or 'username' not in user_id:
        raise ValidationError("Invalid user data")
    return {"message": f"Hello, {user_id['username']}!"}, 200


@auth_bp.route('/refresh_token', methods=['POST'])
def refresh_token():
    """刷新 Token"""
    token = request.headers.get('Authorization')
    if not token:
        raise ValidationError("令牌缺失")

    pattern = r'^\s*(?:Bearer[\s:]+)+(.+)$'  # 关键变化：用 (?:...) 匹配重复的 Bearer
    match = re.match(pattern, token, re.IGNORECASE)
    if match:
        token = match.group(1).strip()

    try:
        # 直接验证 refresh_token
        decoded = verify_token(token, check_blacklist=False)  # refresh_token 无需检查黑名单
        token_type = decoded.get('token_type')

        if token_type == 'access':
            raise TokenError("请使用有效的 Refresh Token")
        print(token)
        # 生成新的 access_token
        response, status = TokenService.refresh_token(token)
        return response, status

    except TokenError as e:
        logger.error(f"Token refresh failed: {str(e)}")
        raise e



@auth_bp.route('/generate_code', methods=['POST'])  # 修正methods参数
@apply_rate_limit("5 per minute")
def generate_code():
    """
    生成验证码并发送给用户（通过手机号或邮箱）
    """
    validated_data = GenerateCodeSchema().load(request.get_json())
    # 调用 AuthService 生成验证码
    code = VerificationCodeService.generate_verification_code(validated_data)
    response_data = {
        "data": {"code": code},  # 返回code到data字段
        "message": "验证码发送成功",
    }
    return create_json_response(response_data, 200)
