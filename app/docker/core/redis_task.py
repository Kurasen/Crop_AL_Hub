import json
from typing import Optional, Dict

from app.core.redis_connection_pool import redis_pool


class RedisTaskQueue:
    """
    基于现有Redis连接池单例的任务队列服务
    通过上下文管理器自动管理连接
    """
    def __init__(self, queue_name: str = 'default_tasks'):
        self.queue_name = queue_name

    def push_task(self, task_data: dict) -> bool:
        """推送任务到队列（使用默认连接池）"""
        with redis_pool.get_redis_connection('default') as conn:
            try:
                return conn.rpush(self.queue_name, json.dumps(task_data)) > 0
            except Exception as e:
                raise RuntimeError(f"任务推送失败: {str(e)}")

    def pop_task(self, timeout: int = 30) -> Optional[dict]:
        """阻塞式获取任务（使用专用任务连接池）"""
        with redis_pool.get_redis_connection('tasks') as conn:
            try:
                _, data = conn.blpop(self.queue_name, timeout=timeout)
                return json.loads(data) if data else None
            except Exception as e:
                raise RuntimeError(f"任务获取失败: {str(e)}")

    def update_status(self, task_id: str, status: str, meta: dict = None) -> None:
        """更新任务状态（使用缓存专用池）"""
        with redis_pool.get_redis_connection('cache') as conn:
            try:
                key = f"task:{task_id}"
                conn.hset(key, mapping={
                    "status": status,
                    "meta": json.dumps(meta or {})
                })
                conn.expire(key, 86400)  # 24小时过期
            except Exception as e:
                raise RuntimeError(f"状态更新失败: {str(e)}")
