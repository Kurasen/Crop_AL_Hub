from app.repositories.Model.model_repo import ModelRepository


class ModelService:
    @staticmethod
    def get_all_models():
        # 获取所有模型数据
        return ModelRepository.get_all_models()

    @staticmethod
    def get_model_by_id(model_id: int):
        # 获取指定ID的模型
        return ModelRepository.get_model_by_id(model_id)

    @staticmethod
    def get_models_by_cuda(cuda_support: bool):
        # 查询是否支持CUDA的模型
        return ModelRepository.get_models_by_cuda(cuda_support)

    @staticmethod
    def search_models(name=None, input=None, cuda=None, description=None, type=None, page=1, per_page=10, sort_by='accuracy', sort_order='asc'):
        """查询模型，调用Repository层"""
        total_count, models = ModelRepository.search_models(
            name=name,
            input=input,
            cuda=cuda,
            description=description,
            type=type,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            per_page=per_page
        )

        return {
            "data": [model.to_dict() for model in models],
            "total_count": total_count,
            "page": page,
            "per_page": per_page,
            "total_pages": (total_count + per_page - 1) // per_page
        }