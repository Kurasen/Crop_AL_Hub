import re
import jwt
from app.blueprint.utils.JWT import verify_token, generate_token
from app.blueprint.utils.auth_utils import verify_password
from app.models.user import User
from app.repositories.User.login_attempt_repo import LoginAttemptsRepository
from flask import current_app
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError


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
        return User.query.filter(filters.get(login_type) == login_identifier).first()

    # 根据用户名来查询用户
    @staticmethod
    def get_user_by_username(username):
        return User.query.filter_by(username=username).first()

    # 根据电话号码来查询用户
    @staticmethod
    def get_user_by_telephone(telephone):
        return User.query.filter_by(telephone=telephone).first()

    # 根据邮箱来查询用户
    @staticmethod
    def get_user_by_email(email):
        return User.query.filter_by(email=email).first()

    @staticmethod
    def increment_login_attempts(login_identifier):
        """增加登录失败尝试次数"""
        redis_client = AuthRepository.get_redis_client()
        redis_client.incr(f"login_attempts:{login_identifier}")
        redis_client.expire(f"login_attempts:{login_identifier}", 3600)  # 1小时过期

    @staticmethod
    def reset_login_attempts(login_identifier):
        """重置登录失败次数"""
        redis_client = AuthRepository.get_redis_client()
        redis_client.delete(f"login_attempts:{login_identifier}")

    @staticmethod
    def check_login_attempts(login_identifier):
        """检查登录失败次数"""
        redis_client = AuthRepository.get_redis_client()
        attempts = redis_client.get(f"login_attempts:{login_identifier}")
        return int(attempts) < 5  # 最大 5 次登录尝试

    def refresh_token(token):
        """
        使用 Refresh Token 获取新的 Access Token。
        :return: 返回新的 Access Token，或者错误信息
        """
        try:
            decoded = verify_token(token)  # 解码并验证 JWT
            new_token = generate_token(decoded['user_id'], decoded['username'])
            return {"message": "Token refreshed", "token": new_token}, 200
        except jwt.ExpiredSignatureError:
            return {"message": "Token has expired. Please log in again."}, 401
        except jwt.InvalidTokenError:
            return {"message": "Invalid token. Please log in again."}, 401
