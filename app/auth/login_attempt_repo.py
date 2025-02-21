from app.core.redis_connection_pool import redis_pool

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_TIME = 300  # 5 分钟锁定时间


class LoginAttemptsRepository:
    
    """
    登录尝试数据访问层，负责跟踪用户的登录尝试次数，并记录登录尝试的时间。
    """

    @staticmethod
    def check_login_attempts(login_identifier):
        """
        检查用户的登录尝试次数，如果超过最大尝试次数，返回 False（锁定），否则返回 True（允许登录）。
        """
        with redis_pool.get_redis_connection(pool_name='cache') as redis_client:
            attempts = redis_client.get(login_identifier)  # 获取登录尝试次数
            # 如果没有尝试次数，意味着该用户尚未尝试登录过，返回 True 允许登录
            if attempts is None:
                return True

            # 如果尝试次数大于等于最大限制，返回 False 表示锁定
            return int(attempts) < MAX_LOGIN_ATTEMPTS

    @staticmethod
    def increment_login_attempts(login_identifier):
        """
        增加用户的登录尝试次数，并设置过期时间，确保锁定时间有效。
        """
        with redis_pool.get_redis_connection(pool_name='cache') as redis_client:
            # 增加登录尝试次数
            redis_client.incr(login_identifier)
            # 设置过期时间，确保锁定时间有效
            redis_client.expire(login_identifier, LOCKOUT_TIME)

    @staticmethod
    def reset_login_attempts(login_identifier):
        """
        重置用户的登录尝试次数。
        """
        with redis_pool.get_redis_connection(pool_name='cache') as redis_client:
            redis_client.delete(login_identifier)
