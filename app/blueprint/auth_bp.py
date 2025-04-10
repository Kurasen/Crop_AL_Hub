import re

from flask import request, Blueprint, g

from app.core.redis_connection_pool import redis_pool
from app.schemas.base_schema import apply_rate_limit
from app.schemas.auth_schema import UserCreateSchema, UserLoginSchema, GenerateCodeSchema
from app.token.token_service import TokenService
from app.utils.json_encoder import create_json_response
from app.token.JWT import verify_token, TokenBlacklist, auth_required
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
@auth_required
def post():
    """登出功能"""
    user_id = g.current_user.id

    with redis_pool.get_redis_connection(pool_name='user') as redis_client:
        lock_key = f"logout_lock:{user_id}"
        lock = redis_client.set(lock_key, 'locked', nx=True, ex=5)  # 5 秒锁
        if not lock:
            redis_client.ttl(lock_key)
            raise AuthenticationError("Too many users, please try again later.")
        try:
            # 获取当前令牌的payload
            current_payload = g.current_user_payload

            # 撤销Access Token
            TokenBlacklist.add_to_blacklist(
                jti=current_payload['jti'],
                token_type='access',
                exp_timestamp=current_payload['exp']
            )

            # # 可选：撤销关联的Refresh Token（需业务逻辑支持）
            # if 'linked_refresh_jti' in current_payload:
            #     TokenBlacklist.add_to_blacklist(
            #         jti=current_payload['linked_refresh_jti'],
            #         token_type='refresh',
            #         exp_timestamp=get_refresh_token_exp(current_payload['linked_refresh_jti'])
            #     )
            TokenRepository.delete_user_token(user_id, token_type='access')
            TokenRepository.delete_user_token(user_id, token_type='refresh')
            logger.info(f"用户 {user_id} 登出成功")
            return create_json_response({"message": "登出成功"}, 204)
        except Exception as e:
            logger.info(f"用户 {user_id} 登出失败")
            return create_json_response({"error": {
                "message": str(e)
            }}, 400)
        finally:
            # 确保 Redis 锁被释放
            redis_client.delete(lock_key)


# 受保护接口：需要使用 JWT 认证
@auth_bp.route('/protected', methods=['GET'])
@auth_required
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
