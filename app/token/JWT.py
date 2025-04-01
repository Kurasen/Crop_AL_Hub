import math
import uuid
from typing import Union

import jwt
from datetime import datetime, timedelta, timezone
from flask import request, g
from functools import wraps

from app import User
from app.config import JWTConfig  # 载入配置
from app.core.exception import TokenError, ValidationError, logger
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


def get_jwt_identity():
    """
    解析 `access_token` 并返回 `jti`，确保 logout 用的是 `access_token`
    """
    # 优先从 g 对象获取已解析的 payload
    if hasattr(g, 'current_user_payload'):
        payload = g.current_user_payload
    else:
        # 如果 g 中没有，再解析 Token（兼容性处理）
        token = request.headers.get('Authorization', '')
        if not token.startswith('Bearer '):
            raise TokenError("Token is missing")
        token = token[len('Bearer '):]
        payload = verify_token(token)

    # 确保是 Access Token
    if payload.get("token_type") != "access":
        raise TokenError("Logout must use access_token")

    return payload["jti"]


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            # 严格处理 Authorization 头
            auth_header = request.headers.get('Authorization', '')
            if not auth_header:
                raise TokenError("缺少或无效的授权标头")

            token = auth_header.split(" ")[1].strip()
            if not token:
                raise TokenError("空令牌")  # 验证 Token 并获取 payload
            payload = verify_token(token)
            # 将 payload 存入全局对象 g
            g.current_user = User.query.get(payload['user_id'])
            g.current_user_payload = payload

            # 传递 payload 给路由函数
            return f(*args, **kwargs)
        except TokenError as e:
            raise TokenError(str(e))

    return decorated
