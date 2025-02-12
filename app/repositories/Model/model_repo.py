import re

from app.exception.errors import ValidationError
from app.models.model import Model


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
    def search_models(name=None, input=None, cuda=None, description=None, type=None, page=1, per_page=10, sort_by='accuracy', sort_order='asc'):
        query = Model.query
        if name:
            query = query.filter(Model.name.like(f"%{name}%"))
        if input:
            query = query.filter(Model.input.like(f"%{input}"))
        if cuda is not None:
            query = query.filter(Model.cuda == cuda)
        if description:
            query = query.filter(Model.description.like(f"%{description}%"))
        if type:
            if re.search(r"[^\u4e00-\u9fa5,，; ；]", type):
                raise ValidationError("Invalid type input. Only Chinese characters, spaces, commas, and semicolons "
                                      "are allowed.")

            tags = re.split(r'[,\s;，；]+', type)
            tags = [tag.strip() for tag in tags if tag.strip()]

            for tag in tags:
                query = query.filter(Model.type.ilike(f"%{tag}%"))
        # 排序逻辑
        if sort_by in ['accuracy', 'sales', 'stars', 'likes']:
            if sort_order == 'desc':
                query = query.order_by(getattr(Model, sort_by).desc(), Model.id.asc())  # 降序
            else:
                query = query.order_by(getattr(Model, sort_by).asc(), Model.id.asc())  # 升序
        else:
            raise ValidationError("Invalid sort field. Only 'accuracy', 'sales', 'stars', and 'likes' are allowed.")


        # 总数
        total_count = query.count()

        # 分页查询
        models = query.offset((page - 1) * per_page).limit(per_page).all()

        return total_count, models
