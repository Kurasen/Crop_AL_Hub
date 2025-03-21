from app.utils.tag_filtering_utils import process_and_filter_tags
from app.core.exception import ValidationError
from app.exts import db
from app.model.model import Model

# 定义排序字段的枚举类型（例如：stars, size, etc.）
SORT_BY_CHOICES = ['accuracy', 'likes']


class ModelRepository:
    @staticmethod
    def get_all_models():
        """获取所有模型"""
        return Model.query.all()

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
    def search_models(params: dict):
        query = Model.query
        if params.get('name'):
            query = query.filter(Model.name.ilike(f"%{params.get('name')}%"))

        if params.get('input'):
            query = query.filter(Model.input.like(f"%{params.get('input')}"))

        if params.get('cuda'):
            query = query.filter(Model.cuda == params.get('cuda'))

        if params.get('description'):
            query = query.filter(Model.description.ilike(f"%{params.get('description')}%"))

        if params.get('type'):
            query = process_and_filter_tags(query, Model.type, params.get('type'))

        # 排序逻辑
        if params.get('sort_by') in SORT_BY_CHOICES:
            if params.get('sort_order') == 'desc':
                query = query.order_by(getattr(Model, params.get('sort_by')).desc(), Model.id.asc())  # 降序
            else:
                query = query.order_by(getattr(Model, params.get('sort_by')).asc(), Model.id.asc())  # 升序
        elif not params.get('sort_by') and not params.get('sort_order'):
            # 如果没有提供排序字段和排序顺序，直接跳过排序，返回原始查询
            pass
        else:
            raise ValidationError("Invalid sort field. Only 'accuracy' and 'likes' are allowed.")

        # 总数
        total_count = query.count()

        # 分页查询
        models = query.offset((params.get('page', 1) - 1) * params.get('per_page', 5)).limit(
            params.get('per_page', 5)).all()

        print(f"SQL Query: {str(query)}")

        return total_count, models

    @staticmethod
    def save_model(model_instance):
        """通用保存方法，用于创建和更新"""
        db.session.add(model_instance)
        return model_instance

    @staticmethod
    def delete_model(model):
        """删除模型"""
        db.session.delete(model)
