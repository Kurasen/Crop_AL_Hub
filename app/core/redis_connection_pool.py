import redis


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
        #self.logger.info(f"Getting Redis client for database: {db}")
        return redis.Redis(connection_pool=self.pool[db])

