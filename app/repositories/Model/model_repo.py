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

    @classmethod
    def search_models(cls, search_term=None, input_type=None, cuda=None, description=None, page=1, per_page=10):
        query = Model.query  # 使用 SQLAlchemy 的 Model.query

        if search_term:
            query = query.filter(Model.name.like(f"%{search_term}%"))  # 使用 Model 类的字段进行过滤
        if input_type:
            query = query.filter(Model.input.like(f"%{input_type}"))
        if cuda is not None:
            query = query.filter(Model.cuda == cuda)
        if description:
            query = query.filter(Model.description.like(f"%{description}%"))

        # 分页查询
        total = query.count()
        results = query.offset((page - 1) * per_page).limit(per_page).all()

        # 打印查询的 SQL 和结果
        print(f"Query SQL: {str(query)}")
        print(f"Query results: {results}")

        return {
            "data": [result.to_dict() for result in results],
            "page": page,
            "per_page": per_page,
            "total": total
        }
