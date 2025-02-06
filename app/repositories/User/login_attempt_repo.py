import redis
from flask import current_app

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_TIME = 300  # 5 分钟锁定时间


class LoginAttemptsRepository:
    
    """
    登录尝试数据访问层，负责跟踪用户的登录尝试次数，并记录登录尝试的时间。
    """
    @staticmethod
    def get_redis_client():
        """获取 Redis 客户端，默认使用 db=1"""
        redis_pool = current_app.config['REDIS_POOL']
        return redis_pool.get_redis_client('user')  # 获取用户登录相关数据的 Redis 连接（db=1）


    @staticmethod
    def check_login_attempts(login_identifier):
        """
        检查用户的登录尝试次数，如果超过最大尝试次数，返回 False（锁定），否则返回 True（允许登录）。
        """
        redis_client = LoginAttemptsRepository.get_redis_client()  # 获取 db=1 的客户端
        attempts = redis_client.get(login_identifier)  # 获取登录尝试次数
        return not (attempts and int(attempts) >= MAX_LOGIN_ATTEMPTS)

    @staticmethod
    def increment_login_attempts(login_identifier):
        """
        增加用户的登录尝试次数，并设置过期时间，确保锁定时间有效。
        """
        redis_client = LoginAttemptsRepository.get_redis_client()
        redis_client.incr(login_identifier)
        redis_client.expire(login_identifier, LOCKOUT_TIME)


    @staticmethod
    def reset_login_attempts(login_identifier):
        """
        重置用户的登录尝试次数。
        """
        redis_client = LoginAttemptsRepository.get_redis_client()
        redis_client.delete(login_identifier)