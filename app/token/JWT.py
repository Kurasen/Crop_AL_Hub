import math
import uuid
from typing import Union

import jwt
from datetime import datetime, timedelta, timezone
from flask import request, g
from functools import wraps

from werkzeug.exceptions import Forbidden

from app import User
from app.config import JWTConfig  # 载入配置
from app.core.exception import TokenError, ValidationError, logger, NotFoundError, PermissionDeniedError, APIError
from app.core.redis_connection_pool import redis_pool


def generate_token(
        user_id: Union[int, str],
        username: str,
        token_type: str = "access"
) -> str:
    """
    合并后的Token生成方法（支持access/refresh）

    参数说明：
    - user_id: 用户唯一标识（支持数字或字符串uuid）
    - username: 用户名
    - token_type: token类型（access/refresh）
    - last_auth_event: 最后一次授权相关事件时间（密码修改/权限变更）
    返回：JWT字符串
    """
    # 参数校验
    if token_type not in ["access", "refresh"]:
        raise ValidationError("无效的token类型")

    if not isinstance(user_id, (int, str)):
        raise TypeError("无效的user_id")

    # if token_type == "refresh" and not last_auth_event:
    #     raise ValueError("refresh token必须提供last_auth_event")

    # 统一生成jti
    jti = str(uuid.uuid4())

    # 设置有效期（安全增强点：动态配置）
    now = datetime.now(timezone.utc)
    exp_delta = JWTConfig.ACCESS_EXPIRE if token_type == "access" else JWTConfig.REFRESH_EXPIRE

    # 构建完整payload
    payload = {
        # 标准声明（RFC 7519）
        "iss": JWTConfig.ISSUER,  # Issuer
        "aud": JWTConfig.AUDIENCE,  # Audience
        "exp": (now + timedelta(seconds=exp_delta)).timestamp(),
        "nbf": now,  # Not Before
        "iat": now,  # Issued At

        # 自定义声明
        "user_id": str(user_id),  # 统一转换为字符串
        "username": username,
        "jti": jti,  # JWT ID
        "token_type": token_type,

        # 安全声明
        #"lat": last_auth_event.timestamp() if last_auth_event else None
    }

    # 选择密钥（安全关键点：access/refresh使用不同密钥）
    secret_key = JWTConfig.ACCESS_SECRET_KEY if token_type == "access" else JWTConfig.REFRESH_SECRET_KEY

    return jwt.encode(
        payload,
        secret_key,
        algorithm="HS256"
    )


# 保留原有接口兼容性
def generate_access_token(user_id, username):
    return generate_token(user_id, username, 'access')


def generate_refresh_token(user_id, username):
    return generate_token(user_id, username, 'refresh')


class TokenBlacklist:
    @staticmethod
    def add_to_blacklist(jti: str, token_type: str, exp_timestamp: int):
        """动态设置黑名单过期时间"""
        remaining_ttl = exp_timestamp - int(datetime.now(timezone.utc).timestamp())
        remaining_ttl = math.floor(remaining_ttl)
        remaining_ttl = max(0, remaining_ttl)

        if remaining_ttl > 0:
            with redis_pool.get_redis_connection(pool_name='user') as redis_client:
                redis_client.setex(
                    f"{JWTConfig.BLACKLIST_REDIS_KEY}:{token_type}:{jti}",
                    remaining_ttl,
                    "revoked"
                )
        else:
            logger.warning(f"Token已过期，无需加入黑名单 jti: {jti}")


# 验证 JWT
def verify_token(token, check_blacklist=True):
    try:

        unverified_hear = jwt.get_unverified_header(token)
        token_type = unverified_hear.get("token_type", "access")
        secret_key = JWTConfig.ACCESS_SECRET_KEY if token_type == "access" else JWTConfig.REFRESH_SECRET_KEY

        payload = jwt.decode(
            token,
            secret_key,
            issuer=JWTConfig.ISSUER,
            audience=JWTConfig.AUDIENCE,
            algorithms=["HS256"]
        )
        # 检查黑名单
        if check_blacklist:
            jti = payload["jti"]
            redis_key = f"{JWTConfig.BLACKLIST_REDIS_KEY}:{token_type}:{jti}"
            with redis_pool.get_redis_connection(pool_name='user') as redis_client:
                exists = redis_client.exists(redis_key)
                if exists:
                    raise TokenError("令牌已被撤销")
        return payload  # 返回解码后的 Payload（有效载荷）, payload 是字典
    except jwt.ExpiredSignatureError:
        raise TokenError("令牌已过期")  # 抛出自定义的认证错误
    except jwt.InvalidTokenError:
        raise TokenError("认证失败，错误的令牌")  # 抛出自定义的认证错误


# def get_jwt_identity():
#     """
#     解析 `access_token` 并返回 `jti`，确保 logout 用的是 `access_token`
#     """
#     # 优先从 g 对象获取已解析的 payload
#     if hasattr(g, 'current_user_payload'):
#         payload = g.current_user_payload
#     else:
#         # 如果 g 中没有，再解析 Token（兼容性处理）
#         token = request.headers.get('Authorization', '')
#         if not token.startswith('Bearer '):
#             raise TokenError("Token is missing")
#         token = token[len('Bearer '):]
#         payload = verify_token(token)
#
#     # 确保是 Access Token
#     if payload.get("token_type") != "access":
#         raise TokenError("Logout must use access_token")
#
#     return payload["jti"]


def token_required(model=None, id_param=None, owner_field='user_id', admin_required=False,
                   resource_map=None):
    """
    增强版装饰器：集成权限校验
    :param model: 需要校验的模型类 (e.g. App)
    :param id_param: URL 中的资源ID参数名 (e.g. 'app_id')
    :param owner_field: 模型中的用户关联字段 (默认 'user_id')
    :param admin_required:管理员权限要求
    :param resource_map: 动态资源映射，格式为 {upload_type: (ModelClass, 'id_param', 'owner_field')}

    """
    def decorator(f):
        @wraps(f)
        def decorated_token(*args, **kwargs):
            # --- Token验证逻辑 ---
            auth_header = request.headers.get('Authorization', '')
            if not auth_header:
                raise TokenError("缺少或无效的授权标头")

            token = auth_header.split(" ")[1].strip()
            if not token:
                raise TokenError("空令牌")  # 验证 Token 并获取 payload

            try:
                payload = verify_token(token)
                # 将 payload 存入全局对象 g
                g.current_user = User.query.get(payload['user_id'])
                g.current_user_payload = payload

            except TokenError as e:
                raise TokenError(str(e))

            # --- 管理员权限检查 ---
            if admin_required and g.current_user.role_id != 0:
                logger.info(f"拒绝非管理员访问，用户ID: {g.current_user.id}")
                raise PermissionDeniedError("需要管理员权限")

                # --- 动态资源权限校验 ---
            if resource_map:
                upload_type = kwargs.get('upload_type')
                if upload_type in resource_map:
                    model_cls, id_param_name, owner_field_name = resource_map[upload_type]
                    resource_id = kwargs.get('data_id')  # 从路由参数获取资源ID

                    instance = model_cls.query.get(resource_id)
                    if not instance:
                        raise NotFoundError(f"资源不存在: {upload_type} ID {resource_id}")

                    # 权限校验：管理员或所有者
                    is_admin = g.current_user.role_id == 0
                    is_owner = getattr(instance, owner_field_name) == g.current_user.id
                    if not (is_admin or is_owner):
                        raise PermissionDeniedError(f"无权操作此 {upload_type}")

                    # 注入实例到参数（可选）
                    kwargs[f'{upload_type}_instance'] = instance

            # --- 权限自动校验 ---
            if model and id_param:
                resource_id = kwargs.get(id_param)
                if not resource_id:
                    raise APIError(f"URL 缺少必要参数: {id_param}")

                instance = model.query.get(resource_id)
                if not instance:
                    raise NotFoundError()

                # 验证权限：管理员无需检查所有权，普通用户需验证所有者
                is_admin = g.current_user.role_id == 0
                is_owner = getattr(instance, owner_field) == g.current_user.id

                if not (is_admin or is_owner):
                    raise PermissionDeniedError("无权操作此资源")

                if id_param in kwargs:
                    del kwargs[id_param]  # 删除指定参数
                kwargs['instance'] = instance  # 注入实例

            return f(*args, **kwargs)
        #print(f"[Token装饰器调试] 原函数名: {f.__name__}, 装饰后函数名: {decorated_token.__name__}")
        return decorated_token
    return decorator
