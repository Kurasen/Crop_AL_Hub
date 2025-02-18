import re

from app.common.tag_utils import process_and_filter_tags
from app.exception.errors import ValidationError
from app.exts import db
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
    def search_models(name=None, input=None, cuda=None, description=None, type=None, page=1, per_page=10,
                      sort_by='accuracy', sort_order='asc'):
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
            query = process_and_filter_tags(query, Model.type, type)

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

    @staticmethod
    def create_model(data):
        """在数据库中创建一个新的模型"""
        # 创建模型对象
        model = Model(
            name=data["name"],
            image=data.get("image"),
            input=data["input"],
            description=data["description"],
            cuda=data.get("cuda", False),
            instruction=data.get("instruction"),
            output=data.get("output"),
            accuracy=data.get("accuracy"),
            type=data.get("type"),
            sales=data.get("sales"),
            stars=data.get("stars"),
            likes=data.get("likes")
        )

        # 将模型添加到数据库
        db.session.add(model)
        return model

    @staticmethod
    def update_model(model, **updates):
        """更新模型信息"""
        # 遍历传入的更新字段，将其应用到模型实例
        for key, value in updates.items():
            if hasattr(model, key):  # 检查模型是否有这个字段
                setattr(model, key, value)
            else:
                raise ValidationError(f"Field '{key}' does not exist in the model")
        return model

    @staticmethod
    def delete_model(model):
        """删除模型"""
        db.session.delete(model)
