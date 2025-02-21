# import os
# from contextlib import contextmanager
#
# import redis
#
# from app.core.exception import RedisConnectionError
#
#
# def create_redis_pool():
#     redis_host = os.getenv('REDIS_HOST', 'localhost')
#     redis_port = os.getenv('REDIS_PORT', 6379)
#     redis_password = os.getenv('REDIS_PASSWORD', None)
#     try:
#         # 连接到 Redis
#         redis_pool = RedisConnectionPool(redis_host, redis_port, redis_password)
#         # 检查连接
#         with redis_pool.get_redis_connection('default') as redis_client:
#             redis_client.ping()  # 执行 ping 操作
#         print("Connected to Redis successfully!")
#         return redis_pool
#     except Exception as e:
#         print(f"Error connecting to Redis: {e}")
#         raise e
#
#
# class RedisConnectionPool:
#
#     def __init__(self, redis_host='redis', redis_port=6379, redis_password=None):
#         self.redis_host = redis_host
#         self.redis_port = redis_port
#         self.redis_password = redis_password
#
#         # 创建连接池
#         self.pool = {
#             "default": redis.ConnectionPool(
#                 host=self.redis_host,
#                 port=self.redis_port,
#                 password=self.redis_password,
#                 db=0,  # 默认数据库 db0
#                 decode_responses=True,
#                 max_connections=100,  # 最大连接数
#                 socket_timeout=5,  # 超时时间设置为 5 秒
#             ),
#             "user": redis.ConnectionPool(
#                 host=self.redis_host,
#                 port=self.redis_port,
#                 password=self.redis_password,
#                 db=1,  # 用户相关操作使用 db1
#                 decode_responses=True,
#                 max_connections=100,
#                 socket_timeout=5,
#             ),
#             "cache": redis.ConnectionPool(
#                 host=self.redis_host,
#                 port=self.redis_port,
#                 password=self.redis_password,
#                 db=2,  # 缓存数据使用 db2
#                 decode_responses=True,
#                 max_connections=50,
#                 socket_timeout=5,
#             )
#         }
#
#     def get_redis_client(self, db='default'):
#         """获取 Redis 客户端，根据传入的 db 参数选择不同的数据库"""
#         if db not in self.pool:
#             raise ValueError(f"Invalid Redis database: {db}")
#         try:
#             return redis.Redis(connection_pool=self.pool[db])
#         except redis.exceptions.ConnectionError as e:
#             # 连接错误处理
#             raise RedisConnectionError(f"Failed to connect to Redis: {str(e)}")
#         except redis.exceptions.TimeoutError as e:
#             # 超时错误处理
#             raise RedisConnectionError(f"Redis connection timeout: {str(e)}")
#         except Exception as e:
#             # 其他异常
#             raise RedisConnectionError(f"Unexpected Redis error: {str(e)}")
#
#     @contextmanager
#     def get_redis_connection(self, db='default'):
#         """
#         上下文管理器，提供 Redis 连接，并确保连接会被正确释放。
#         """
#         try:
#             client = self.get_redis_client(db)
#             yield client
#         except redis.exceptions.RedisError as e:
#             raise RedisConnectionError(f"Redis connection failed for db {db}: {str(e)}")
#         finally:
#             pass  # 不需要手动释放连接，因为 Redis 客户端会自动管理连接池


import os
import logging
from contextlib import contextmanager
import redis
from typing import Dict, Any
from app.core.exception import RedisConnectionError

# 配置日志
logger = logging.getLogger(__name__)


class RedisConnectionPool:
    """
    Redis 连接池单例类，全局唯一实例
    通过上下文管理器安全使用连接
    """
    _instance = None  # 单例实例
    _initialized = False  # 防止重复初始化

    def __new__(cls, *args, **kwargs):
        # 单例核心逻辑：确保只创建一个实例
        if not cls._instance:
            cls._instance = super().__new__(cls)
            logger.info("RedisConnectionPool 单例已创建")
        return cls._instance

    def __init__(self):
        # 防止 __init__ 被多次调用（Python 单例常见问题）
        if self.__class__._initialized:
            return
        self.__class__._initialized = True
        # 从环境变量读取配置（生产环境推荐）
        self.redis_host = os.getenv('REDIS_HOST', 'redis')
        self.redis_port = int(os.getenv('REDIS_PORT', 6379))
        self.redis_password = os.getenv('REDIS_PASSWORD', None)
        # 初始化连接池
        self.pools = self._create_pools()
        logger.info("Redis 连接池初始化完成")

    def _create_pools(self) -> Dict[str, redis.ConnectionPool]:
        """创建不同用途的连接池（按数据库隔离）"""
        return {
            'default': redis.ConnectionPool(
                host=self.redis_host,
                port=self.redis_port,
                password=self.redis_password,
                db=0,
                max_connections=100,
                socket_timeout=5,
                decode_responses=True,
                health_check_interval=30  # 自动健康检查
            ),
            'user': redis.ConnectionPool(
                host=self.redis_host,
                port=self.redis_port,
                password=self.redis_password,
                db=1,
                max_connections=50,
                socket_timeout=5,
                decode_responses=False  # 二进制数据需保留原始 bytes
            ),
            "cache": redis.ConnectionPool(
                host=self.redis_host,
                port=self.redis_port,
                password=self.redis_password,
                db=2,
                max_connections=50,
                socket_timeout=5,
                decode_responses=True
            )
        }

    @contextmanager
    def get_redis_connection(self, pool_name: str = 'default') -> redis.Redis:
        """
        上下文管理器：安全获取和释放连接
        用法：
            with redis_pool.get_connection('default') as conn:
                conn.set('key', 'value')
        """
        conn = None
        try:
            if pool_name not in self.pools:
                raise ValueError(f"无效的连接池名称: {pool_name}")

            # 从指定池获取连接
            conn = redis.Redis(connection_pool=self.pools[pool_name])

            # 验证连接有效性
            if not conn.ping():
                raise RedisConnectionError("Redis 连接无响应")

            logger.debug(f"成功获取 {pool_name} 连接")
            yield conn  # 在此处交出连接供使用
        except redis.RedisError as e:
            logger.error(f"Redis 操作失败: {str(e)}")
            raise RedisConnectionError(f"Redis 错误: {str(e)}")
        finally:
            if conn:
                conn.close()  # 显式释放连接回池（非必须但更规范）
                logger.debug(f"{pool_name} 连接已释放")


# 初始化单例（全局唯一）
redis_pool = RedisConnectionPool()
