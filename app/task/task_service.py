from app.core.exception import DatabaseError, NotFoundError, logger
from app.exts import db
from app.task.task_repo import TaskRepository


class TaskService:
    VALID_STATUSES = {'PENDING', 'STARTED', 'SUCCESS', 'FAILURE', 'RETRY'}

    @staticmethod
    def get_all_tasks():
        # 获取所有模型数据
        tasks = TaskRepository.get_all_tasks()
        if not tasks:
            raise DatabaseError("No models found.")
        return [TaskService._convert_to_dict(task) for task in tasks]

    @staticmethod
    def _convert_to_dict(task):
        """将数据集转换为字典格式"""
        # 假设 dataset 是一个模型对象，转换为字典
        return task.to_dict()

    @staticmethod
    def get_task_by_id(task_id: int):
        # 获取指定ID的模型
        task = TaskRepository.get_task_by_id(task_id)
        if not task:
            raise NotFoundError(f"未找到task_id为 {task_id} 的任务")
        return task

    @staticmethod
    def search_tasks(search_params: dict):
        """查询模型，调用Repository层"""
        try:
            total_count, tasks = TaskRepository.search_tasks(search_params)

            return {
                "data": {
                    "items": [TaskService._convert_to_dict(task) for task in tasks],
                    "total": total_count,
                    "page": search_params.get("page", 1),
                    "per_page": search_params.get("per_page", 5),
                    "total_pages": (total_count + search_params.get("per_page", 5) - 1) // search_params.get("per_page",
                                                                                                             5)  # 计算总页数
                },
            }
        except Exception as e:
            logger.error(f"Error occurred while searching models: {str(e)}")
            raise e

    @staticmethod
    def update_task(task_instance):
        """更新模型"""
        try:
            # 获取模型对象
            TaskRepository.save_task(task_instance)
            db.session.commit()
            return task_instance.to_dict(), 200
        except Exception as e:
            db.session.rollback()
            logger.error(f"Unexpected error while updating model : {str(e)}")
            raise e

    @staticmethod
    def delete_task(task_id):
        """删除模型"""
        try:
            task = TaskService.get_task_by_id(task_id)
            TaskRepository.delete_task(task)
            db.session.commit()
            return {"message": "Task deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error occurred while deleting model {task_id}: {str(e)}")
            raise e
