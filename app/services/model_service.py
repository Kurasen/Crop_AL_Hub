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
    def search_models(search_term=None, input_type=None, cuda=None, describe=None, page=1, per_page=10):
        # 调用 Repository 层
        return ModelRepository.search_models(
            search_term=search_term,
            input_type=input_type,
            cuda=cuda,
            describe=describe,
            page=page,
            per_page=per_page
        )