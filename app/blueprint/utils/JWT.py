import jwt
from datetime import datetime, timedelta
from flask import jsonify, request
from functools import wraps
from app.config import Config  # 载入配置

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
        #print(f"payload: {payload}, type: {type(payload)}")  # 输出调试信息
        return payload, None  # payload 是字典
    except jwt.ExpiredSignatureError:
        return None, "Token has expired"
    except jwt.InvalidTokenError:
        return None, "Invalid token"


# 装饰器：保护路由
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'] # 从请求头中获取 Token

        if not token:
            return jsonify({"message": "Token is missing"}), 401

        try:
            # 检查是否存在 Bearer 前缀，若有则去掉
            if token.startswith("Bearer "):
                token = token.split(" ")[1]  # 去掉 Bearer 前缀
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return {"message": "Token has expired"}, 401
        except jwt.InvalidTokenError:
            return {"message": "Invalid token"}, 401

        # 确保解码后的数据是字典类型
        if not isinstance(data, dict):
            return {"message": "Invalid token data"}, 400

        # 将解码后的数据传递给视图函数
        return f(current_user=data, *args, **kwargs)

    return decorated


