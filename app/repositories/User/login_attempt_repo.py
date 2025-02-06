from flask import current_app

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
        attempts = current_app.redis_client.get(login_identifier)# 从 Flask app 获取 redis_client
        if attempts and int(attempts) >= MAX_LOGIN_ATTEMPTS:
            return False  # 超过最大尝试次数，锁定用户
        return True  # 没有超过最大尝试次数，允许登录

    @staticmethod
    def increment_login_attempts(login_identifier):
        """
        增加用户的登录尝试次数，并设置过期时间，确保锁定时间有效。
        """

        current_app.redis_client.incr(login_identifier)
        current_app.redis_client.expire(login_identifier, LOCKOUT_TIME)  # 设置锁定时限，过期后尝试次数将清除


    @staticmethod
    def reset_login_attempts(login_identifier):
        """
        重置用户的登录尝试次数。
        """
        current_app.redis_client.delete(login_identifier)