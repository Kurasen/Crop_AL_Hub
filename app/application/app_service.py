from app.application.app import App
from app.application.app_repo import AppRepository
from app.core.exception import DatabaseError, NotFoundError, logger, ServiceException
from app.exts import db
from app.utils.common.json_encoder import ResponseBuilder


class AppService:

    @staticmethod
    def get_all_tasks():
        # 获取所有模型数据
        tasks = AppRepository.get_all_apps()
        if not tasks:
            raise DatabaseError("未查询到数据")
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
            raise NotFoundError("应用未找到")
        return app

    @staticmethod
    def search_apps(search_params: dict):
        """查询模型，调用Repository层"""
        try:
            # 统一分页参数处理
            page = max(1, int(search_params.get("page", 1)))
            per_page = min(100, max(1, int(search_params.get("per_page", 5))))

            # 传递分页参数到Repository
            total_count, apps = AppRepository.search_apps(
                search_params,
                page=page,
                per_page=per_page
            )

            # 构建返回数据
            items = [AppService._convert_to_dict(app) for app in apps]
            return ResponseBuilder.paginated_response(
                items=items,
                total_count=total_count,
                page=page,
                per_page=per_page
            )
        except Exception as e:
            logger.error("搜索模型错误｜参数= %s｜异常= %s", search_params, str(e), exc_info=True)
            raise ServiceException("查询服务暂时不可用")

    @staticmethod
    def create_app(instance: App):
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
    def update_app(instance: App):
        """创建模型"""
        try:
            AppRepository.save_app(instance)
            db.session.commit()
            return instance.to_dict(), 200
        except Exception as e:
            db.session.rollback()
            logger.error(f"更新应用失败｜ID={instance.id}｜错误={str(e)}")
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
