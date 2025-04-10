import math
import uuid
from typing import Union

import jwt
from datetime import datetime, timedelta, timezone
from flask import request, g
from functools import wraps

from werkzeug.exceptions import Forbidden

from app import User, Model, Dataset
from app.config import JWTConfig  # 载入配置
from app.core.exception import TokenError, ValidationError, logger, NotFoundError, PermissionDeniedError, APIError
from app.core.redis_connection_pool import redis_pool
from app.exts import db


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


# def token_required(model=None, id_param=None, owner_field='user_id', admin_required=False):
#     """
#     增强版装饰器：集成权限校验
#     :param model: 需要校验的模型类 (e.g. App)
#     :param id_param: URL 中的资源ID参数名 (e.g. 'app_id')
#     :param owner_field: 模型中的用户关联字段 (默认 'user_id')
#     :param admin_required:管理员权限要求
#     """
#
#     def decorator(f):
#         @wraps(f)
#         def decorated_token(*args, **kwargs):
#             # --- Token验证逻辑 ---
#             auth_header = request.headers.get('Authorization', '')
#             if not auth_header:
#                 raise TokenError("缺少或无效的授权标头")
#
#             token = auth_header.split(" ")[1].strip()
#             if not token:
#                 raise TokenError("空令牌")  # 验证 Token 并获取 payload
#
#             try:
#                 payload = verify_token(token)
#                 # 将 payload 存入全局对象 g
#                 g.current_user = User.query.get(payload['user_id'])
#                 g.current_user_payload = payload
#
#             except TokenError as e:
#                 raise TokenError(str(e))
#
#             # --- 管理员权限检查 ---
#             if admin_required and g.current_user.role_id != 0:
#                 logger.info(f"拒绝非管理员访问，用户ID: {g.current_user.id}")
#                 raise PermissionDeniedError("需要管理员权限")
#
#             # --- 权限自动校验 ---
#             if model and id_param:
#                 resource_id = kwargs.get(id_param)
#                 if not resource_id:
#                     raise APIError(f"URL 缺少必要参数: {id_param}")
#
#                 instance = model.query.get(resource_id)
#                 if not instance:
#                     raise NotFoundError()
#
#                 # 验证权限：管理员无需检查所有权，普通用户需验证所有者
#                 is_admin = g.current_user.role_id == 0
#                 is_owner = getattr(instance, owner_field) == g.current_user.id
#
#                 if not (is_admin or is_owner):
#                     raise PermissionDeniedError("无权操作此资源")
#
#                 if id_param in kwargs:
#                     del kwargs[id_param]  # 删除指定参数
#                 kwargs['instance'] = instance  # 注入实例
#
#             return f(*args, **kwargs)
#
#         #print(f"[Token装饰器调试] 原函数名: {f.__name__}, 装饰后函数名: {decorated_token.__name__}")
#         return decorated_token
#
#     return decorator


# ------------------------------
# 基础登录校验装饰器（外部可直接使用）
# ------------------------------
def auth_required(f):
    """独立登录校验装饰器"""

    @wraps(f)
    def decorated(*args, **kwargs):
        # 原有验证逻辑
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

        return f(*args, **kwargs)

    return decorated


# ------------------------------
# 管理员校验装饰器（内置登录校验）
# ------------------------------
def admin_required(f):
    """管理员校验（自动包含登录校验）"""

    @wraps(f)
    @auth_required  # 自动嵌套登录校验
    def decorated(*args, **kwargs):
        # 已通过login_required校验
        if g.current_user.role_id != 0:
            raise PermissionDeniedError("需要管理员权限")

        return f(*args, **kwargs)

    return decorated


# ------------------------------
# 资源所有者装饰器（动态/静态二合一）
# ------------------------------
def resource_owner(
        model=None,  # 静态指定模型类 (优先级低于动态类型)
        resource_type_param=None,  # 动态模型参数名 (e.g. 'upload_type')
        id_param='id',  # 资源ID参数名 (对应URL中的参数)
        owner_field='user_id',  # 资源所有者字段名
        allow_admin=True,  # 是否允许管理员跳过校验
        inject_instance=True  # 是否向视图函数注入资源实例 (静态资源默认启用)
):
    """资源权限校验装饰器 (需配合_auth_required使用)"""

    def decorator(f):
        @wraps(f)
        @auth_required
        def decorated(*args, **kwargs):
            nonlocal model  # 允许动态修改模型类

            # 动态模型类型解析 (当指定资源类型参数时)
            if resource_type_param:
                type_key = kwargs.get(resource_type_param)
                if not type_key:
                    raise ValidationError(f"缺少资源类型参数: {resource_type_param}")
                model = get_model_by_type(type_key)  # 会抛出错误如果类型无效

            # 参数完整性检查
            if not model:
                raise ValidationError("未指定资源模型类")
            resource_id = kwargs.get(id_param)
            if not resource_id:
                raise APIError(f"URL缺少必要参数: {id_param}")

            # 获取资源实例 (不存在则立即报错)
            instance = model.query.get(resource_id)
            if not instance:
                raise NotFoundError("指定的资源不存在")

            # 权限校验流程
            is_admin = g.current_user.role_id == 0  # 使用role_id保持兼容性
            if not (allow_admin and is_admin):  # 非管理员需要校验所有者
                if getattr(instance, owner_field) != g.current_user.id:
                    raise PermissionDeniedError("无权操作此资源")

            # 参数注入处理
            if inject_instance and not resource_type_param:
                # 静态资源：删除原始ID参数，注入实例参数
                if id_param in kwargs:
                    del kwargs[id_param]
                kwargs['instance'] = instance
            else:
                # 动态资源：保留原始参数，同时存入全局对象
                g.resource_instance = instance

            return f(*args, **kwargs)

        return decorated

    return decorator


def get_model_by_type(resource_type):
    """资源类型到模型的映射"""
    resource_model_map = {
        'model': Model,
        'user': User,
        'dataset': Dataset
    }
    model = resource_model_map.get(resource_type)
    if not model:
        raise ValidationError("不支持的资源类型")
    return model
