from app.application.app import App
from app.application.app_repo import AppRepository
from app.core.exception import DatabaseError, NotFoundError, logger
from app.exts import db


class AppService:

    @staticmethod
    def get_all_tasks():
        # 获取所有模型数据
        tasks = AppRepository.get_all_apps()
        if not tasks:
            raise DatabaseError("No models found.")
        return [AppService._convert_to_dict(task) for task in tasks]

    @staticmethod
    def _convert_to_dict(app):
        """将数据集转换为字典格式"""
        # 假设 dataset 是一个模型对象，转换为字典
        return app.to_dict()

    @staticmethod
    def get_app_by_id(app_id: int):
        # 获取指定ID的模型
        app = AppRepository.get_app_by_id(app_id)
        if not app:
            raise NotFoundError(f"应用不存在")
        return app

    @staticmethod
    def search_apps(search_params: dict):
        """查询模型，调用Repository层"""
        try:
            total_count, apps = AppRepository.search_apps(search_params)

            return {
                "data": {
                    "items": [AppService._convert_to_dict(app) for app in apps],
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
    def save_app(instance: App):
        """创建模型"""
        try:
            AppRepository.save_app(instance)
            db.session.commit()
            return instance.to_dict(), 201
        except Exception as e:
            db.session.rollback()
            logger.error(f"创建应用失败｜ID={instance.id}｜错误={str(e)}")
            raise e

    @staticmethod
    def delete_app(instance: App):
        """删除模型"""
        try:
            AppRepository.delete_app(instance)
            db.session.commit()
            return {"message": "数据删除成功"}, 200
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error occurred while deleting app : {str(e)}")
            raise e
