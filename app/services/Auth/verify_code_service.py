import random
import string

from flask import current_app

from app.core.redis_connection_pool import RedisConnectionPool


# 使用 Redis 缓存验证码的服务
class VerificationCodeService:
    def __init__(self, redis_connection_pool: RedisConnectionPool):
        self.redis_connection_pool = redis_connection_pool

    @staticmethod
    def generate_verification_code(self, identifier, login_type):
        """
        生成验证码，并将其存入缓存中
        :param identifier: 电话或邮箱
        :param login_type: 'telephone' 或 'email'
        :return: 生成的验证码
        """
        # 生成一个6位数的验证码
        code = ''.join(random.choices(string.digits, k=6))

        # 获取 Redis 客户端（选择缓存数据库 db=2）
        cache_client = self.redis_connection_pool.get_redis_client(db='cache')

        # 设置缓存，存储验证码并设置过期时间
        cache_key = f"{login_type}_{identifier}_code"
        cache_client.setex(cache_key, 300, code)  # 过期时间为 300 秒（5分钟）

        # 发送验证码到用户（这里只是打印，实际应通过邮件或短信发送）
        current_app.logger.info(f"Sending {login_type} verification code to {identifier}: {code}")

        return code

    def validate_code(self, identifier, login_type, code):
        """
        验证验证码
        :param identifier: 电话或邮箱
        :param login_type: 'telephone' 或 'email'
        :param code: 用户输入的验证码
        :return: True 如果验证码正确，False 如果错误
        """
        # 获取 Redis 客户端（选择缓存数据库 db=2）
        cache_client = self.redis_connection_pool.get_redis_client(db='cache')

        # 获取缓存中的验证码
        cache_key = f"{login_type}_{identifier}_code"
        stored_code = cache_client.get(cache_key)

        if stored_code is None:
            # 验证码不存在或者已过期
            current_app.logger.warning(f"Verification code for {login_type} {identifier} has expired or doesn't exist.")
            return False

        if stored_code == code:
            # 验证成功
            current_app.logger.info(f"Verification code for {login_type} {identifier} is correct.")
            return True
        else:
            # 验证失败
            current_app.logger.warning(f"Incorrect verification code for {login_type} {identifier}.")
            return False
