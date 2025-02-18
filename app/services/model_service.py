from app.blueprint.utils.upload_file import save_uploaded_file
from app.exception.errors import DatabaseError, ValidationError
from app.repositories.Model.model_repo import ModelRepository
from app.services.dataset_service import DatasetService


class ModelService:
    @staticmethod
    def get_all_models():
        # 获取所有模型数据
        models = ModelRepository.get_all_models()
        if not models:
            raise DatabaseError("No models found.")
        return [ModelService._convert_to_dict(model) for model in models]

    @staticmethod
    def _convert_to_dict(model):
        """将数据集转换为字典格式"""
        # 假设 dataset 是一个模型对象，转换为字典
        return model.to_dict()  # 假设你有一个 to_dict 方法

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

    # 处理模型和文件，获取图像处理路径和模型信息
    @staticmethod
    def process_model_and_file(model_id, uploaded_file):
        try:
            # 尝试将 model_id 转换为整数
            model_id = int(model_id)
        except ValueError:
            raise ValidationError("model_id 应该是整数类型")

        # 检查 model_id 是否有效
        if not ModelService.get_model_by_id(model_id):
            raise ValidationError("无效的 model_id")

        # 处理文件上传
        file_path = save_uploaded_file(uploaded_file)

        # 处理图像（这里只是模拟）
        processed_image_path = ModelService.process_image(file_path)

        # 4. 构造模型信息
        model_info = {
            'model_id': model_id,
            'accuracy': 92.5,  # 模拟准确率
            'description': f'Model {model_id} processed successfully'
        }

        return processed_image_path, model_info

    @staticmethod
    def get_model_accuracy(model_id: int, dataset_id: int) -> str:
        model = ModelService.get_model_by_id(model_id)
        dataset = DatasetService.get_dataset_by_id(dataset_id)

        # 校验模型和数据集是否存在
        if not model:
            raise ValidationError(f"Model with ID {model_id} not found")
        if not dataset:
            raise ValidationError(f"Dataset with ID {dataset_id} not found")

        # 返回准确率信息
        return f"Model_{model_id} trained on Dataset_{dataset_id} has an accuracy of {model_id * dataset_id}%"
