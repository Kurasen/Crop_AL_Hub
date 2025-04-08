# app_repository.py
from typing import Optional

from app.application.app import App
from app.core.exception import ValidationError
from app.exts import db
from app.utils.apply_sort import apply_sorting


class AppRepository:
    @staticmethod
    def get_all_apps():
        """获取所有应用"""
        return App.query.all()

    @staticmethod
    def get_app_by_id(app_id: int) -> Optional[App]:
        """通过ID获取应用"""
        return App.query.get(app_id)

    @staticmethod
    def search_apps(params: dict):
        query = App.query

        if params.get('name'):
            query = query.filter(App.name.ilike(f"%{params.get('name')}%"))

        if params.get('description'):
            query = query.filter(App.description.like(f"%{params.get('description')}%"))

        SORT_BY_CHOICES = ['created_at', 'updated_at']

        # 排序逻辑
        if params.get('sort_by') in SORT_BY_CHOICES:
            if params.get('sort_order') == 'desc':
                query = query.order_by(getattr(App, params.get('sort_by')).desc(), App.id.asc())  # 降序
            else:
                query = query.order_by(getattr(App, params.get('sort_by')).asc(), App.id.asc())  # 升序
        elif not params.get('sort_by') and not params.get('sort_order'):
            # 如果没有提供排序字段和排序顺序，直接跳过排序，返回原始查询
            pass
        else:
            raise ValidationError("Invalid sort field. Only 'accuracy', 'likes', 'created_at' and 'updated_at' are "
                                  "allowed.")

        # 总数
        total_count = query.count()

        # 分页查询
        models = query.offset((params.get('page', 1) - 1) * params.get('per_page', 5)).limit(
            params.get('per_page', 5)).all()

        print(f"SQL Query: {str(query)}")

        return total_count, models

    @staticmethod
    def save_app(app_data):
        """通用保存方法，用于创建和更新"""
        db.session.add(app_data)
        return app_data

    @staticmethod
    def delete_app(app):
        """删除模型"""
        db.session.delete(app)
