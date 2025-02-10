import uuid

import jwt
from datetime import datetime, timedelta
from flask import jsonify, request
from functools import wraps
from app.config import Config  # 载入配置
from app.exception.errors import AuthenticationError
from app.repositories.Token.token_repo import TokenRepository

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
        'exp': datetime.utcnow() + timedelta(minutes=1),  # 设置过期时间为当前时间加 15 分钟
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
    redis_client = TokenRepository.get_redis_client()
    redis_client.set(f"{BLACKLIST_REDIS_KEY}:{jti}", "revoked", ex=timedelta(days=7))


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
            redis_client = TokenRepository.get_redis_client()
            if redis_client.exists(f"{BLACKLIST_REDIS_KEY}:{jti}"):
                print(f"Token with jti {jti} is in the blacklist.")  # 输出黑名单信息
                raise AuthenticationError("Token has been revoked")

        return payload  # 返回解码后的 Payload（有效载荷）, payload 是字典
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")  # 抛出自定义的认证错误
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid token")  # 抛出自定义的认证错误


# 解析 JWT 并获取用户 ID
def get_jwt_identity():
    """
    解析 `access_token` 并返回 `jti`，确保 logout 用的是 `access_token`
    """
    token = request.headers.get('Authorization')
    if not token or not token.startswith('Bearer '):
        raise AuthenticationError("Token is missing")

    token = token[len('Bearer '):]
    payload = verify_token(token)

    if "access" not in payload["token_type"]:
        raise AuthenticationError("Logout must be done using access_token")

    return payload["jti"]


# 装饰器：保护路由
def token_required(f):
    """
    装饰器，用于保护需要认证的路由，确保请求中包含有效的 token。
    :param f: 视图函数
    :return: 包装后的视图函数
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            payload = verify_token(request.headers.get('Authorization').split(" ")[1])
            return f(current_user=payload, *args, **kwargs)
        except AuthenticationError as e:
            raise AuthenticationError(str(e))

    return decorated
