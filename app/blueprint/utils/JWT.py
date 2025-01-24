import jwt
import datetime
from flask import jsonify, request
from functools import wraps
from app.config import Config  # 载入配置

SECRET_KEY = Config.SECRET_KEY


##未设置缓存token,每次登录token都会刷新

# 生成 JWT
def generate_token(user_id, username):
    payload = {
        "id": user_id,
        "username": username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)  # 有效期1小时
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
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
        token = request.headers.get('Authorization')  # 从请求头中获取 Token
        if not token:
            return jsonify({"message": "Token is missing"}), 401

        try:
            # 解码 JWT
            token = token.split(" ")[1]  # 假设格式为 "Bearer <token>"
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
