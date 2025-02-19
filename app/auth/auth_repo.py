from app.core.redis_connection_pool import RedisConnectionPool
from app.exts import db
from app.user.user import User
from flask import current_app

redis_pool = RedisConnectionPool()


class AuthRepository:
    """
    认证服务层，负责处理用户的登录验证、密码校验等业务逻辑。
    """

    @staticmethod
    def get_redis_client(db='user'):
        """获取 Redis 客户端，默认使用 db=1"""
        return redis_pool.get_redis_client(db)   # 获取用户登录相关数据的 Redis 连接（db=1）

    # 根据用户提供的登录类型查询用户
    @staticmethod
    def get_user_by_identifier(login_identifier, login_type):
        """根据用户提供的登录类型查询用户"""
        filters = {
            'telephone': User.telephone,
            'email': User.email
        }
        user = User.query.filter(filters.get(login_type) == login_identifier).first()
        return user

    # 根据用户名来查询用户
    @staticmethod
    def get_user_by_username(username):
        user = User.query.filter_by(username=username).first()
        return user

    # 根据电话号码来查询用户
    @staticmethod
    def get_user_by_telephone(telephone):
        user = User.query.filter_by(telephone=telephone).first()
        return user

    # 根据邮箱来查询用户
    @staticmethod
    def get_user_by_email(email):
        user = User.query.filter_by(email=email).first()
        return user

    @staticmethod
    def save_user(user):
        db.session.add(user)
