from sqlalchemy.orm import joinedload

from app.utils.common.common_service import CommonService
from app.core.exception import ValidationError, logger, ServiceException
from app.exts import db
from app.model.model import Model
from sqlalchemy.orm import joinedload

from app.utils.common.pagination import PaginationHelper


class ModelRepository:
    # 定义可排序字段映射
    SORT_FIELD_MAPPING = {
        'accuracy': Model.accuracy,
        'likes': Model.likes,
        'created_at': Model.created_at,
        'updated_at': Model.updated_at
    }

    @staticmethod
    def get_all_models():
        """获取所有模型"""
        return Model.query.all().options(joinedload(Model.user))

    @staticmethod
    def get_model_by_id(model_id: int):
        """根据模型ID获取单个模型"""
        return Model.query.get(model_id)

    @staticmethod
    def get_models_by_cuda(cuda_support: bool):
        """根据是否支持CUDA查询模型"""
        return Model.query.filter_by(cuda=cuda_support).all()

    @staticmethod
    def get_all_type_strings():
        """直接查询所有模型的 type 字段（仅返回非空值）"""
        return [
            result[0]
            for result in Model.query.with_entities(Model.type).filter(Model.type is not None).all()
            if result[0]  # 过滤空字符串
        ]

    @staticmethod
    def search_models(params: dict, page: int = 1, per_page: int = 10):
        try:
            # 基础查询+急加载
            query = Model.query.options(
                joinedload(Model.user),
            )

            if params.get('name'):
                query = query.filter(Model.name.ilike(f"%{params.get('name')}%"))

            if params.get('input'):
                query = query.filter(Model.input.like(f"%{params.get('input')}"))

            if params.get('cuda'):
                query = query.filter(Model.cuda == params.get('cuda'))

            if params.get('description'):
                query = query.filter(Model.description.ilike(f"%{params.get('description')}%"))

            if params.get('type'):
                query = CommonService.process_and_filter_tags(query, Model.type, params.get('type'))

            # 调用通用分页方法
            return PaginationHelper.paginate(
                query=query,
                page=page,
                per_page=per_page,
                sort_mapping=ModelRepository.SORT_FIELD_MAPPING,
                sort_by=params.get('sort_by'),
                sort_order=params.get('sort_order', 'asc')
            )
        except Exception as e:
            logger.error("模型查询失败｜%s", str(e), exc_info=True)
            raise


    @staticmethod
    def delete_model(model):
        """删除模型"""
        db.session.delete(model)
