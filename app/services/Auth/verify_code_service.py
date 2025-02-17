import hashlib
import hmac
import random
import secrets
import string
import time
import redis

from flask import current_app
from app.core.redis_connection_pool import RedisConnectionPool
from app.exception.errors import ValidationError


# 使用 Redis 缓存验证码的服务
class VerificationCodeService:
    CODE_EXPIRE = 300  # 5分钟
    RATE_LIMIT_TIME = 60  # 限制一分钟内不能重复请求

    def __init__(self):
        # 初始化时传递 Redis 配置信息
        self.redis_connection_pool = RedisConnectionPool()

    @staticmethod
    def generate_verification_code(login_type, login_identifier):
        """
        生成验证码，并将其存入缓存中
        :param login_identifier: 电话或邮箱
        :param login_type: 'telephone' 或 'email'
        :return: 生成的验证码
        """
        # 生成一个6位数的验证码
        code = ''.join(secrets.choice(string.digits) for _ in range(6))

        # 获取 Redis 客户端（选择缓存数据库 db=2）

        cache_client = RedisConnectionPool().get_redis_client(db='cache')  # 使用单例获取 Redis 客户端
        current_app.logger.info(f"Redis client connected: {cache_client}")
        # 设置缓存，存储验证码并设置过期时间
        cache_key = VerificationCodeService._generate_redis_key(login_type, login_identifier)
        rate_limit_key = f"rate_limit:{cache_key}"

        # 检查是否超过一分钟内已经生成过验证码
        last_generated_time = cache_client.get(rate_limit_key)
        if last_generated_time:
            # 如果验证码已经生成并且未超过一分钟
            time_diff = time.time() - float(last_generated_time)
            if time_diff < VerificationCodeService.RATE_LIMIT_TIME:
                raise ValidationError("请在一分钟后重试获取验证码")

        try:
            # 设置验证码缓存，确保 cache_key 是 bytes 类型
            cache_client.setex(cache_key, VerificationCodeService.CODE_EXPIRE, code)
            current_app.logger.info(f"验证码已存储: {cache_key}")

            # 设置限制时间的缓存，记录验证码生成时间
            cache_client.setex(rate_limit_key, VerificationCodeService.RATE_LIMIT_TIME, time.time())
            current_app.logger.info(f"验证码生成时间已记录: {rate_limit_key}")

        except redis.exceptions.RedisError as e:
            current_app.logger.error(f"Redis存储失败: {str(e)}")
            raise
        # 发送验证码到用户（这里只是打印，实际应通过邮件或短信发送）
        current_app.logger.info(f"Sending {login_type} verification code to {login_identifier}: {code}")

        return code

    @staticmethod
    def validate_code(login_type, login_identifier, code):
        """
        验证验证码
        :param login_identifier: 电话或邮箱
        :param login_type: 'telephone' 或 'email'
        :param code: 用户输入的验证码
        :return: True 如果验证码正确，否则抛出 ValidationError
        """
        redis_key = VerificationCodeService._generate_redis_key(login_type, login_identifier)
        cache_client = RedisConnectionPool().get_redis_client(db='cache')
        try:
            pipe = cache_client.pipeline()
            pipe.get(redis_key)
            result = pipe.execute()  # 返回格式 [stored_code, delete_count]

            # 明确处理返回值
            stored_code = result[0] if len(result) > 0 else None
            delete_count = result[1] if len(result) > 1 else 0

            print(stored_code, delete_count)
            if stored_code is None:
                current_app.logger.warning(f"验证码不存在或已过期: {redis_key}")
                raise ValidationError("验证码已过期或未发送")

            if stored_code != code:
                current_app.logger.warning(f"验证码不匹配: 输入={code}, 存储={stored_code}")
                raise ValidationError("验证码错误")

            # 验证成功后删除验证码
            pipe.delete(redis_key)
            pipe.execute()  # 执行删除操作

            return True
        except redis.exceptions.RedisError as e:
            current_app.logger.error(f"Redis操作失败: {str(e)}")
            raise ValidationError("验证服务暂时不可用")

    @staticmethod
    def _generate_redis_key(login_type, login_identifier):
        # 获取 SECRET_KEY，确保它是 bytes 类型
        secret_key = current_app.config['SECRET_KEY']

        # 如果 SECRET_KEY 是字符串类型，则转为 bytes
        if isinstance(secret_key, str):
            secret_key = secret_key.encode('utf-8')

        # 确保 login_type 和 login_identifier 拼接后的 msg 参数是 bytes 类型

        # 使用 HMAC 增强安全性，key 和 msg 都是 bytes 类型
        h = hmac.new(
            key=secret_key,  # 确保是 bytes 类型
            msg=f"{login_type}:{login_identifier}".encode('utf-8'),  # msg 必须是 bytes 类型
            digestmod=hashlib.sha256
        )

        redis_key = f"vc:{h.hexdigest()}"
        print(f"Generated redis_key: {redis_key}")  # 打印生成的 redis_key
        return redis_key
