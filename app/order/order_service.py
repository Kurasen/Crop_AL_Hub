from contextlib import contextmanager
from typing import Optional

from flask import current_app

from app.core.exception import RedisConnectionError
from app.core.redis_connection_pool import redis_pool
from app.exts import db
from app.order.order import OrderStatus, Order, OrderType


class OrderService:
    @staticmethod
    @contextmanager
    def get_redis_client(pool_name: str = 'cache'):
        """获取Redis连接的上下文管理器"""
        try:
            with redis_pool.get_redis_connection(pool_name=pool_name) as client:
                yield client
        except Exception as e:
            current_app.logger.info(f"Redis连接失败: {str(e)}")
            raise

    @classmethod
    def get_model_sales_count(cls, model_id: int) -> int:
        """获取模型销售数量（带缓存）"""
        cache_key = f"model_sales:{model_id}"

        # 尝试从缓存获取
        try:
            with cls.get_redis_client() as redis_client:
                cached = redis_client.get(cache_key)
                if cached is not None:
                    return int(cached)
        except RedisConnectionError:
            current_app.logger.info("Redis缓存不可用，使用数据库查询")
        # 缓存未命中，查询数据库
        count = cls._get_real_time_model_sales(model_id)

        # 异步更新缓存
        cls._update_cache_async(cache_key, count)

        return count

    @classmethod
    def _get_real_time_model_sales(cls, model_id: int) -> int:
        """实时数据库查询"""
        return Order.query.filter_by(
            model_id=model_id,
            status=OrderStatus.COMPLETED
        ).count()

    @classmethod
    def _update_cache_async(cls, key: str, value: int, ttl: int = 300):
        """异步更新缓存（使用独立连接）"""

        def update_task():
            try:
                with cls.get_redis_client() as redis_client:
                    redis_client.setex(key, ttl, value)
                    current_app.logger.debug(f"缓存更新成功: {key}")
            except Exception as e:
                current_app.logger.error(f"缓存更新失败: {str(e)}")

        # 使用线程池或Celery执行异步任务
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(update_task)

    @classmethod
    def invalidate_sales_cache(cls, model_id: Optional[int] = None, dataset_id: Optional[int] = None):
        """缓存失效逻辑"""
        try:
            with cls.get_redis_client() as redis_client:
                if model_id:
                    redis_client.delete(f"model_sales:{model_id}")
                if dataset_id:
                    redis_client.delete(f"dataset_sales:{dataset_id}")
                # 同时失效排行榜缓存
                redis_client.delete("sales_leaderboard")
        except RedisConnectionError as e:
            current_app.logger.info(f"缓存失效失败: {str(e)}")


# 在订单状态变更时调用
def update_order_status(order_id: int, new_status: OrderStatus):
    order = Order.query.get(order_id)
    old_status = order.status

    if old_status == new_status:
        return

    # 更新订单状态
    order.status = new_status
    db.session.commit()

    # 失效相关缓存
    if order.order_type == OrderType.MODEL and order.model_id:
        OrderService.invalidate_sales_cache(model_id=order.model_id)
    elif order.order_type == OrderType.DATASET and order.dataset_id:
        OrderService.invalidate_sales_cache(dataset_id=order.dataset_id)
