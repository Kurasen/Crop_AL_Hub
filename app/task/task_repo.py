from app import Task
from app.core.exception import ValidationError, logger
from app.exts import db
from app.utils.apply_sort import apply_sorting


class TaskRepository:

    @staticmethod
    def get_all_tasks():
        """获取所有模型"""
        return Task.query.all()

    @staticmethod
    def get_task_by_id(task_id: int):
        """根据模型ID获取单个模型"""
        return Task.query.get(task_id)

    @staticmethod
    def search_tasks(params: dict):
        query = Task.query

        if params.get('status'):
            query = query.filter(Task.status == params.get('status'))

        if params.get('remarks'):
            query = query.filter(Task.remarks.ilike(f"%{params.get('remarks')}%"))

        if params.get('result_info'):
            query = query.filter(Task.result_info.ilike(f"%{params.get('result_info')}%"))

        SORT_BY_CHOICES = ['created_at', 'updated_at']

        query = apply_sorting(
            query=query,
            params=params,
            model=Task,
            valid_sort_fields=SORT_BY_CHOICES
        )

        # 总数
        total_count = query.count()

        # 分页查询
        tasks = query.offset((params.get('page', 1) - 1) * params.get('per_page', 5)).limit(
            params.get('per_page', 5)).all()

        print(f"SQL Query: {str(query)}")

        return total_count, tasks

    @staticmethod
    def save_task(task_instance):
        """通用保存方法，用于创建和更新"""
        db.session.add(task_instance)
        return task_instance

    @staticmethod
    def delete_task(task):
        """删除模型"""
        db.session.delete(task)
