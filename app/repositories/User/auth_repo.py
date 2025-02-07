import jwt
from app.blueprint.utils.JWT import verify_token, generate_token
from app.exception.errors import AuthenticationError
from app.models.user import User
from flask import current_app

from app.repositories.Token.token_repo import TokenRepository


class AuthRepository:
    """
    认证服务层，负责处理用户的登录验证、密码校验、Token刷新等业务逻辑。
    """
    @staticmethod
    def get_redis_client():
        """获取 Redis 客户端，默认使用 db=1"""
        redis_pool = current_app.config['REDIS_POOL']
        return redis_pool.get_redis_client('user')  # 获取用户登录相关数据的 Redis 连接（db=1）

    # 根据用户提供的登录类型查询用户
    @staticmethod
    def get_user_by_identifier(login_identifier, login_type):
        """根据用户提供的登录类型查询用户"""
        filters = {
            'username': User.username,
            'telephone': User.telephone,
            'email': User.email
        }
        user = User.query.filter(filters.get(login_type) == login_identifier).first()
        if not user:
            raise AuthenticationError(f"User with {login_type} '{login_identifier}' not found.")
        return user

    # 根据用户名来查询用户
    @staticmethod
    def get_user_by_username(username):
        user = User.query.filter_by(username=username).first()
        if not user:
            raise AuthenticationError(f"User with username '{username}' not found.")
        return user

    # 根据电话号码来查询用户
    @staticmethod
    def get_user_by_telephone(telephone):
        user = User.query.filter_by(telephone=telephone).first()
        if not user:
            raise AuthenticationError(f"User with telephone '{telephone}' not found.")
        return user

    # 根据邮箱来查询用户
    @staticmethod
    def get_user_by_email(email):
        user = User.query.filter_by(email=email).first()
        if not user:
            raise AuthenticationError(f"User with email '{email}' not found.")
        return user

    @staticmethod
    def refresh_token(token):
        """
        使用 Refresh Token 获取新的 Access Token。
        :return: 返回新的 Access Token，或者错误信息
        """
        decoded = verify_token(token)  # 解码并验证 JWT
        if not decoded:
            raise AuthenticationError("Invalid token. Please log in again.")
        new_token = generate_token(decoded['user_id'], decoded['username'])

        # 存储新的 Token 到 Redis
        TokenRepository.set_user_token(decoded['user_id'], new_token)

        return {"message": "Token refreshed", "token": new_token}, 200
