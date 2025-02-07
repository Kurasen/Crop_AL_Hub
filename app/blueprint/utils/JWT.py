import jwt
from datetime import datetime, timedelta
from flask import jsonify, request
from functools import wraps
from app.config import Config  # 载入配置
from app.exception.errors import AuthenticationError

SECRET_KEY = Config.SECRET_KEY


# 生成 JWT
def generate_token(user_id, username):
    expiration = timedelta(hours=1)
    exp = datetime.utcnow() + expiration
    token = jwt.encode({
        'user_id': user_id,
        'username': username,
        'exp': exp
    }, SECRET_KEY, algorithm='HS256')
    return token


# 验证 JWT
def verify_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload, None  # payload 是字典
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")  # 抛出自定义的认证错误
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid token")  # 抛出自定义的认证错误


# 装饰器：保护路由
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization']
        elif 'Authorization' in request.args:  # 如果没有 header 中的 token，可以从查询参数获取(为了方便在swagger上测试))
            token = request.args['Authorization']

        if not token:
            return jsonify({"message": "Token is missing"}), 401

        # 检查是否存在 Bearer 前缀，若有则去掉
        if token.startswith("Bearer "):
            token = token.split(" ")[1]  # 去掉 Bearer 前

        # 验证 token
        payload, error = verify_token(token)
        if error:
            raise AuthenticationError(error)  # 如果验证失败，抛出认证错误

        # 将解码后的数据传递给视图函数
        return f(current_user=payload, *args, **kwargs)

    return decorated


