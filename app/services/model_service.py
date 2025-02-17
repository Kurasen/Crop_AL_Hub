from app.blueprint.utils.upload_file import UploadFile
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
    def search_models(name=None, input=None, cuda=None, description=None, type=None, page=1, per_page=10,
                      sort_by='accuracy', sort_order='asc'):
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

    # 模拟的图像处理函数
    @staticmethod
    def process_image(image_file):
        return image_file

    @staticmethod
    def handle_model_and_file(model_id, uploaded_file):
        # 校验并获取 model
        model = ModelRepository.get_model_by_id(model_id)

        # 处理文件上传
        file_path = UploadFile.save_uploaded_file(uploaded_file)

        # 处理图像（这里只是模拟）
        processed_image_path = ModelService.process_image(file_path)

        return processed_image_path, model
