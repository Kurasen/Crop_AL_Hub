
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
        # 从环境变量读取配置
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
