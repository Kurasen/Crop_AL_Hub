import jwt
from datetime import datetime, timedelta
from flask import jsonify, request
from functools import wraps
from app.config import Config  # 载入配置
from app.exception.errors import AuthenticationError
from app.repositories.Token.token_repo import TokenRepository

SECRET_KEY = Config.SECRET_KEY


# 生成 access_token（15 分钟有效）
def generate_access_token(user_id, username):
    """
    用于生成 access_token，包含用户的 ID 和用户名，且有效期为 15 分钟。

    :param user_id: 用户 ID
    :param username: 用户名
    :return: 生成的 access_token
    """
    # 设置 payload（有效载荷），包括用户信息和过期时间
    token = jwt.encode({
        'user_id': user_id,
        'username': username,
        'exp': datetime.utcnow() + timedelta(minutes=15)  # 设置过期时间为当前时间加 15 分钟
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
    token = jwt.encode({
        'user_id': user_id,
        'username': username,
        'exp': datetime.utcnow() + timedelta(days=7)  # 设置过期时间为当前时间加 7 天
    }, SECRET_KEY, algorithm='HS256')  # 使用 HS256 算法和密钥进行加密
    return token


# 验证 JWT
def verify_token(token):
    print(f"Verifying token: {token}", flush=True)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        print(f"Decoded payload: {payload}", flush=True)
        # 从 Redis 中获取存储的 Token
        stored_token = TokenRepository.get_user_token(payload["user_id"], "access")
        # 兼容 bytes 和 str 类型
        if isinstance(stored_token, bytes):
            stored_token = stored_token.decode("utf-8")

        if not stored_token or stored_token != token:
            raise AuthenticationError("Token is invalid or has been revoked")

        return payload  # payload 是字典
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")  # 抛出自定义的认证错误
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid token")  # 抛出自定义的认证错误


# 刷新 token
def refresh_token(old_refresh_token):
    """
    使用 refresh_token 获取新的 access_token
    """
    decoded = verify_token(old_refresh_token)  # 验证并解码 refresh_token
    user_id = decoded['user_id']
    username = decoded['username']

    # 检查 Refresh Token 是否仍然存在
    stored_refresh_token = TokenRepository.get_user_token(user_id, "refresh")
    if not stored_refresh_token or stored_refresh_token.decode("utf-8") != old_refresh_token:
        raise AuthenticationError("Refresh Token is invalid or has been revoked")

    # 生成新的 Access Token 和新的 Refresh Token
    new_access_token = generate_access_token(user_id, username)
    new_refresh_token = generate_refresh_token(user_id, username)

    # 存储新的 Refresh Token，并删除旧的
    TokenRepository.delete_user_token(user_id, 'refresh')  # 删除旧的 Refresh Token
    TokenRepository.set_user_token(user_id, new_refresh_token, 'refresh')

    return {"message": "Token refreshed", "access_token": new_access_token, "refresh_token": new_refresh_token}, 200


# 装饰器：保护路由
def token_required(f):
    """
    装饰器，用于保护需要认证的路由，确保请求中包含有效的 token。
    :param f: 视图函数
    :return: 包装后的视图函数
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        # 从请求头中获取 Token（确保有 Bearer 前缀）
        token = request.headers.get('Authorization')
        if not token:
            raise AuthenticationError("Token is missing")

        # 如果 Token 以 "Bearer " 开头，则去除前缀
        if token.startswith('Bearer '):
            token = token[len('Bearer '):]

        # 验证 Token
        try:
            payload = verify_token(token)
        except AuthenticationError as e:
            # 如果验证失败，抛出自定义的 AuthenticationError 异常
            raise AuthenticationError(str(e))

        # 将解码后的用户信息传递给视图函数
        return f(current_user=payload, *args, **kwargs)

    return decorated
