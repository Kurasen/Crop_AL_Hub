import uuid

import jwt
from datetime import datetime, timedelta
from flask import request, g
from functools import wraps
from app.config import Config  # 载入配置
from app.core.exception import AuthenticationError
from app.core.redis_connection_pool import redis_pool

SECRET_KEY = Config.SECRET_KEY
BLACKLIST_REDIS_KEY = "jwt_blacklist"


# 生成 access_token（15 分钟有效）
def generate_access_token(user_id, username):
    """
    用于生成 access_token和Refresh Token，
    验证 Token，
    添加 Token 到黑名单，
    解析 JWT 获取 jti，
    装饰器 token_required 保护路由

    :param user_id: 用户 ID
    :param username: 用户名
    :return: 生成的 access_token
    """
    # 使用 UUID 来确保 jti 唯一
    jti = str(uuid.uuid4())

    # 设置 payload（有效载荷），包括用户信息和过期时间
    token = jwt.encode({
        'user_id': user_id,
        'username': username,
        'jti': jti,  # jwt黑名单
        'exp': datetime.utcnow() + timedelta(minutes=15),  # 设置过期时间为当前时间加 15 分钟
        'token_type': 'access'  # 添加 token_type 字段来标识类型
    }, SECRET_KEY, algorithm='HS256')  # 使用 HS256 算法和密钥进行加密
    return token


# 生成 refresh_token（7 天有效）
def generate_refresh_token(user_id, username):
    """
    用于生成 refresh_token，包含用户的 ID 和用户名，且有效期为 7 天。

    :param user_id: 用户 ID
    :param username: 用户名
    :return: 生成的 refresh_token
    """
    # 使用 UUID 来确保 jti 唯一
    jti = str(uuid.uuid4())

    token = jwt.encode({
        'user_id': user_id,
        'username': username,
        'jti': jti,
        'exp': datetime.utcnow() + timedelta(days=7),  # 设置过期时间为当前时间加 7 天
        'token_type': 'refresh'
    }, SECRET_KEY, algorithm='HS256')  # 使用 HS256 算法和密钥进行加密
    return token


# 将 Token 加入黑名单
def add_to_blacklist(jti):
    """
    将 JWT 的 jti 添加到黑名单。
    使用 Redis 连接池来获取 Redis 连接，以提高效率。
    """
    with redis_pool.get_redis_connection(pool_name='user') as redis_client:
        # 设置 Redis 中 jti 键的过期时间（例如 7 天）
        redis_client.setex(f"jwt_blacklist:{jti}", 604800, "revoked")


# 验证 JWT
def verify_token(token, check_blacklist=True):
    print(f"Verifying token: {token}", flush=True)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        jti = payload["jti"]
        token_type = payload.get('token_type', None)  # 获取 token_type

        print(f"Decoded token: {payload}")
        print(f"Token type: {token_type}")  # 打印 token 类型（'access' 或 'refresh'）

        # 检查黑名单（只对 access_token 做黑名单检查）
        if check_blacklist and token_type == 'access':
            with redis_pool.get_redis_connection(pool_name='user') as redis_client:
                if redis_client.exists(f"{BLACKLIST_REDIS_KEY}:{jti}"):
                    print(f"Token with jti {jti} is in the blacklist.")  # 输出黑名单信息
                    raise AuthenticationError("令牌已被撤销")

        return payload  # 返回解码后的 Payload（有效载荷）, payload 是字典
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("令牌已过期")  # 抛出自定义的认证错误
    except jwt.InvalidTokenError:
        raise AuthenticationError("认证失败，错误的令牌")  # 抛出自定义的认证错误


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
            raise AuthenticationError("Token is missing")
        token = token[len('Bearer '):]
        payload = verify_token(token)

    # 确保是 Access Token
    if payload.get("token_type") != "access":
        raise AuthenticationError("Logout must use access_token")

    return payload["jti"]


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            # 从请求头获取 Token
            token = request.headers.get('Authorization', '').split(" ")[1]
            # 验证 Token 并获取 payload
            payload = verify_token(token)
            # 将 payload 存入全局对象 g
            g.current_user_payload = payload
            # 传递 payload 给路由函数
            return f(current_user=payload, *args, **kwargs)
        except AuthenticationError as e:
            raise AuthenticationError(str(e))
    return decorated
