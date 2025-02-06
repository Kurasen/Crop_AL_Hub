
from redis import Redis

redis_client = Redis(host='localhost', port=6379, db=0)
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_TIME = 300  # 5 分钟锁定时间


class LoginAttemptsRepository:
    """
    登录尝试数据访问层，负责跟踪用户的登录尝试次数，并记录登录尝试的时间。
    """

    # 获取指定用户的登录尝试记录
    @staticmethod
    def check_login_attempts(login_identifier):
        attempts = redis_client.get(login_identifier)
        if attempts and int(attempts) >= MAX_LOGIN_ATTEMPTS:
            return False  # 锁定，不能登录
        return True

    @staticmethod
    def increment_login_attempts(login_identifier):
        redis_client.incr(login_identifier)
        redis_client.expire(login_identifier, LOCKOUT_TIME)  # 设置锁定时限

    # 重置用户的登录尝试次数
    @staticmethod
    def reset_login_attempts(login_identifier):
        redis_client.delete(login_identifier)
