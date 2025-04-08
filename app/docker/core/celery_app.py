from typing import Dict, List, Any

from celery import Celery
from app.config import Config

from celery import current_app


class CeleryManager:
    _celery = None

    @classmethod
    def init_celery(cls, app=None):
        if not cls._celery:
            # 允许不依赖 Flask 独立创建实例
            cls._celery = Celery(
                'crop_al_hub',  # 固定应用名
                broker=Config.broker_url,
                backend=Config.result_backend,
                # 显式禁用Celery自带的连接池复用
                broker_connection_max_retries=0,
                broker_pool_limit=10,

            )
            # 统一配置加载
            config = {
                key: getattr(Config, key)
                for key in dir(Config)
                if not key.startswith('__')
            }
            cls._celery.conf.update(config)

            if app:
                # 合并Flask配置（优先级更高）
                cls._celery.conf.update(app.config)

                # 容器化环境自动发现任务
                cls._celery.autodiscover_tasks(
                    ['app.docker.core'],
                    force=True,
                    related_name='task'  # 明确任务模块路径
                )

        return cls._celery

    @classmethod
    def get_celery(cls):
        if not cls._celery:
            # 允许命令行环境自动初始化
            cls.init_celery()
        return cls._celery

    @classmethod
    def print_celery_tasks(cls):
        """打印 Celery 任务状态（兼容 Celery 5.3.0+）"""
        inspect = current_app.control.inspect()

        print("\n=== Celery 任务状态报告 ===")

        # 1. 获取活动任务（正在执行）
        active_tasks: Dict[str, List[Dict]] = inspect.active() or {}
        print("\n[运行中的任务]")
        for worker, tasks in active_tasks.items():
            print(f"Worker: {worker}")
            for task in tasks:
                print(f"  ID: {task['id']}")
                print(f"  任务名: {task['name']}")
                print(f"  参数: {task.get('args', '无')}")

        # 2. 获取排队任务（需启用 events）
        reserved_tasks: Dict[str, List[Dict]] = inspect.reserved() or {}
        print("\n[排队中的任务]")
        for worker, tasks in reserved_tasks.items():
            print(f"Worker: {worker}")
            for task in tasks:
                print(f"  ID: {task['id']}")

        # 3. 通过结果后端获取失败任务（需配置 result_backend）
        print("\n[失败的任务]")
        try:
            from celery.result import AsyncResult
            # 获取最近100个任务的ID
            failed_ids: List[str] = current_app.events.State().tasks_by_type('task-failed')[:100]
            for task_id in failed_ids:
                result = AsyncResult(task_id, app=current_app)
                print(f"ID: {task_id}")
                print(f"  异常: {result.result}")  # 异常对象存储在 result 中
        except Exception as e:
            print(f"获取失败任务错误（需启用 events）: {str(e)}")

        # 4. 获取已完成任务
        print("\n[最近完成的任务]")
        try:
            from celery.result import AsyncResult
            completed_ids: List[str] = current_app.events.State().tasks_by_type('task-succeeded')[:10]
            for task_id in completed_ids:
                result = AsyncResult(task_id, app=current_app)
                print(f"ID: {task_id}")
                print(f"  结果: {result.result}")
        except Exception as e:
            print(f"获取完成的任务失败: {str(e)}")

    # 在需要的地方调用
    # if __name__ == '__main__':
    #     print_celery_tasks()
