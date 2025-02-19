from contextlib import contextmanager

import redis

from app.core.exception import RedisConnectionError


class RedisConnectionPool:

    def __init__(self, redis_host='redis', redis_port=6379, redis_password=None):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_password = redis_password

        # 创建连接池
        self.pool = {
            "default": redis.ConnectionPool(
                host=self.redis_host,
                port=self.redis_port,
                password=self.redis_password,
                db=0,  # 默认数据库 db0
                decode_responses=True,
                max_connections=100,  # 最大连接数
                socket_timeout=5,  # 超时时间设置为 5 秒
            ),
            "user": redis.ConnectionPool(
                host=self.redis_host,
                port=self.redis_port,
                password=self.redis_password,
                db=1,  # 用户相关操作使用 db1
                decode_responses=True,
                max_connections=100,
                socket_timeout=5,
            ),
            "cache": redis.ConnectionPool(
                host=self.redis_host,
                port=self.redis_port,
                password=self.redis_password,
                db=2,  # 缓存数据使用 db2
                decode_responses=True,
                max_connections=50,
                socket_timeout=5,
            )
        }

    def get_redis_client(self, db='default'):
        """获取 Redis 客户端，根据传入的 db 参数选择不同的数据库"""
        if db not in self.pool:
            raise ValueError(f"Invalid Redis database: {db}")
        try:
            return redis.Redis(connection_pool=self.pool[db])
        except redis.exceptions.ConnectionError as e:
            # 连接错误处理
            raise RedisConnectionError(f"Failed to connect to Redis: {str(e)}")
        except redis.exceptions.TimeoutError as e:
            # 超时错误处理
            raise RedisConnectionError(f"Redis connection timeout: {str(e)}")
        except Exception as e:
            # 其他异常
            raise RedisConnectionError(f"Unexpected Redis error: {str(e)}")

    @contextmanager
    def get_redis_connection(self, db='default'):
        """
        上下文管理器，提供 Redis 连接，并确保连接会被正确释放。
        """
        try:
            client = self.get_redis_client(db)
            yield client
        except redis.exceptions.RedisError as e:
            raise RedisConnectionError(f"Redis connection failed for db {db}: {str(e)}")
        finally:
            pass  # 不需要手动释放连接，因为 Redis 客户端会自动管理连接池
