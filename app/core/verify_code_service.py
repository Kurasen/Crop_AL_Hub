import hashlib
import hmac
import secrets

import time
import redis

from app.config import Config
from app.core.exception import ValidationError, NotFoundError, RetryAfterError, logger
from app.core.redis_connection_pool import redis_pool


# 使用 Redis 缓存验证码的服务
class VerificationCodeService:
    CODE_EXPIRE = 300  # 5分钟
    RATE_LIMIT_TIME = 60  # 限制一分钟内不能重复请求

    # # 使用 Lua 脚本保证原子性（替代管道+WATCH）
    # LUA_GENERATE_SCRIPT = """
    # local rate_limit_key = KEYS[1]
    # local code_key = KEYS[2]
    # local code = ARGV[1]
    # local current_time = tonumber(ARGV[2])
    #
    # -- 检查限流：获取上次生成时间
    # local last_time = redis.call('GET', rate_limit_key)
    # if last_time and (current_time - tonumber(last_time) < tonumber(ARGV[3])) then
    #     return 0  -- 限流未通过
    # end
    #
    # -- 设置限流时间戳和验证码
    # redis.call('SETEX', rate_limit_key, ARGV[3], current_time)
    # redis.call('SETEX', code_key, ARGV[4], code)
    # return 1  -- 操作成功
    # """

    @staticmethod
    def generate_verification_code(validated_data):
        """
        生成验证码，并将其存入缓存中
        :return: 生成的验证码
        """
        login_identifier = validated_data.get('login_identifier')
        login_type = validated_data.get('login_type')
        # 生成一个6位数的验证码
        #code = ''.join(secrets.choice(string.digits) for _ in range(6))
        code = secrets.randbelow(900000) + 100000

        # 获取 Redis 客户端
        with redis_pool.get_redis_connection(pool_name='cache') as cache_client:

            # 设置缓存，存储验证码并设置过期时间
            cache_key = VerificationCodeService._generate_redis_key(login_type, login_identifier)
            rate_limit_key = f"rate_limit:{cache_key}"

            # 检查是否超过一分钟内已经生成过验证码
            last_generated_time = cache_client.get(rate_limit_key)
            if last_generated_time:
                # 如果验证码已经生成并且未超过一分钟
                time_diff = time.time() - float(last_generated_time)
                if time_diff < VerificationCodeService.RATE_LIMIT_TIME:
                    raise RetryAfterError("验证码已发送，请在一分钟后重试获取验证码", 429)

            try:
                # 设置验证码缓存，确保 cache_key 是 bytes 类型
                cache_client.setex(cache_key, VerificationCodeService.CODE_EXPIRE, code)
                logger.info(f"验证码已存储: {cache_key}")

                # 设置限制时间的缓存，记录验证码生成时间
                cache_client.setex(rate_limit_key, VerificationCodeService.RATE_LIMIT_TIME, time.time())
                logger.info(f"验证码生成时间已记录: {rate_limit_key}")

            except redis.exceptions.RedisError as e:
                logger.error(f"Redis存储失败: {str(e)}")
                raise

            # 发送验证码到用户（这里只是打印，实际应通过邮件或短信发送）
            logger.info(f"Sending {login_type} verification code to {login_identifier}: {code}")

            return code

    #
    # @staticmethod
    # def generate_verification_code(login_type, login_identifier):
    #     # 生成安全验证码
    #     code = ''.join(secrets.choice(string.digits) for _ in range(6))
    #     cache_client = RedisConnectionPool().get_redis_client(db='cache')
    #
    #     # 生成 Redis 键
    #     cache_key = VerificationCodeService._generate_redis_key(login_type, login_identifier)
    #     rate_limit_key = f"rate_limit:{cache_key}"
    #
    #     # 执行 Lua 脚本（原子操作）
    #     result = cache_client.eval(
    #         VerificationCodeService.LUA_GENERATE_SCRIPT,
    #         2,  # KEYS 数量
    #         rate_limit_key,
    #         cache_key,
    #         code,
    #         time.time(),
    #         VerificationCodeService.RATE_LIMIT_TIME,
    #         VerificationCodeService.CODE_EXPIRE
    #     )
    #
    #     # 处理脚本返回结果
    #     if result == 0:
    #         raise ValidationError("请在一分钟后重试获取验证码")
    #
    #     # 异步发送验证码（示例：Celery 任务）
    #     send_verification_code_async.delay(login_type, login_identifier, code)
    #     return code  # 生产环境应移除

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
        print(code)
        try:
            with redis_pool.get_redis_connection(pool_name='cache') as cache_client:
                pipe = cache_client.pipeline()
                pipe.get(redis_key)
                result = pipe.execute()  # 返回格式 [stored_code, delete_count]

                # 明确处理返回值
                stored_code = result[0] if len(result) > 0 else None

                ttl = cache_client.ttl(redis_key)

                if stored_code is None:
                    # 如果没有找到验证码，抛出验证码不存在的异常
                    logger.warning(f"验证码不存在: {redis_key}")
                    raise NotFoundError("验证码未发送", 422)

                if ttl <= 0:
                    # 如果验证码已经被删除，说明验证码已过期
                    logger.warning(f"验证码已过期: {redis_key}")
                    raise ValidationError("验证码已过期", 422)

                # 将存储的 code 从字节转为整数类型
                stored_code = int(stored_code)  # 确保从 Redis 获取的 code 是整数

                if stored_code != code:
                    logger.warning(f"验证码不匹配: 输入={code}, 存储={stored_code}")
                    raise ValidationError("验证码错误", 422)

                # 验证成功后删除验证码
                pipe.delete(redis_key)
                pipe.execute()  # 执行删除操作

                return True
        except redis.exceptions.RedisError as e:
            logger.error(f"Redis操作失败: {str(e)}")
            raise ValidationError("验证服务暂时不可用", 404)

    @staticmethod
    def _generate_redis_key(login_type, login_identifier):
        # 获取 SECRET_KEY，确保它是 bytes 类型
        secret_key = Config.SECRET_KEY

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