# app_repository.py
from typing import Optional

from app.application.app import App
from app.core.exception import ValidationError, logger
from app.exts import db
from app.utils.apply_sort import apply_sorting
from sqlalchemy.orm import joinedload

from app.utils.common.pagination import PaginationHelper


class AppRepository:
    SORT_FIELD_MAPPING = {
        'created_at': App.created_at,
        'updated_at': App.updated_at,
        'likes': App.likes,
        'watches': App.watches
    }
    @staticmethod
    def get_all_apps():
        """获取所有应用"""
        return App.query.all().options(joinedload(App.user))

    @staticmethod
    def get_app_by_id(app_id: int) -> Optional[App]:
        """通过ID获取应用"""
        return App.query.get(app_id)

    @staticmethod
    def search_apps(params: dict, page: int = 1, per_page: int = 10):
        try:
            # 基础查询+急加载
            query = App.query.options(
                joinedload(App.user),
            )

            if params.get('name'):
                query = query.filter(App.name.ilike(f"%{params.get('name')}%"))

            if params.get('description'):
                query = query.filter(App.description.like(f"%{params.get('description')}%"))

            # 调用通用分页方法
            return PaginationHelper.paginate(
                query=query,
                page=page,
                per_page=per_page,
                sort_mapping=AppRepository.SORT_FIELD_MAPPING,
                sort_by=params.get('sort_by'),
                sort_order=params.get('sort_order', 'asc')
            )
        except Exception as e:
            logger.error("模型查询失败｜%s", str(e), exc_info=True)
            raise

    @staticmethod
    def save_app(app_data):
        """通用保存方法，用于创建和更新"""
        db.session.add(app_data)
        return app_data

    @staticmethod
    def delete_app(app):
        """删除模型"""
        db.session.delete(app)
