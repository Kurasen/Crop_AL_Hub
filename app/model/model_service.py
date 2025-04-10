import re
from typing import Set

from app import Model
from app.utils.file_process import save_uploaded_file
from app.core.exception import DatabaseError, ValidationError, FileUploadError, ImageProcessingError, \
    NotFoundError, logger
from app.exts import db
from app.model.model_repo import ModelRepository
from app.dataset.dataset_service import DatasetService


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
        return model.to_dict()

    @staticmethod
    def get_model_by_id(model_id: int):
        # 获取指定ID的模型
        model = ModelRepository.get_model_by_id(model_id)
        if not model:
            raise NotFoundError(f"未找到model_id为 {model_id} 的模型")
        return model

    @staticmethod
    def search_models(search_params: dict):
        """查询模型，调用Repository层"""
        try:
            total_count, models = ModelRepository.search_models(search_params)

            return {
                "data": {
                    "items": [ModelService._convert_to_dict(model) for model in models],
                    "total": total_count,
                    "page": search_params.get("page", 1),
                    "per_page": search_params.get("per_page", 5),
                    "total_pages": (total_count + search_params.get("per_page", 5) - 1) // search_params.get("per_page",
                                                                                                             5)  # 计算总页数
                },
            }
        except Exception as e:
            logger.error(f"Error occurred while searching models: {str(e)}")
            raise e

    @staticmethod
    def get_all_types() -> list[str]:
        """获取所有唯一的类型标签"""
        try:
            # 从数据库获取所有模型的 type 字段
            all_type_strings = ModelRepository.get_all_type_strings()

            # 提取唯一类型
            unique_types: Set[str] = set()  # 显式类型注解
            for type_str in all_type_strings:
                # 处理可能的分隔符（中文；或英文;，避免空格干扰）
                types = re.split(r'[；;]', type_str)
                for t in types:
                    stripped_t: str = t.strip()  # 显式声明为 str
                    if stripped_t:
                        # 如果是必须使用 LiteralString 的场景
                        unique_types.add(stripped_t)

            # 排序后返回列表
            return sorted(unique_types)
        except Exception as e:
            logger.error(f"Error getting types: {str(e)}")
            raise e

    @staticmethod
    def create_model(model_instance):
        """创建模型"""
        try:
            ModelRepository.save_model(model_instance)
            db.session.commit()
            return model_instance.to_dict(), 201
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error occurred while creating model: {str(e)}")
            raise e

    @staticmethod
    def update_model(model_instance):
        """更新模型"""
        try:
            # 获取模型对象
            ModelRepository.save_model(model_instance)
            db.session.commit()
            return model_instance.to_dict(), 200
        except Exception as e:
            db.session.rollback()
            logger.error(f"Unexpected error while updating model : {str(e)}")
            raise e

    @staticmethod
    def delete_model(instance: Model):
        """删除模型"""
        try:
            ModelRepository.delete_model(instance)
            db.session.commit()
            return {"message": "数据删除成功"}, 200
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error occurred while deleting model {instance.id}: {str(e)}")
            raise e

    # 模拟的图像处理函数
    @staticmethod
    def process_image(image_file):
        return image_file

    # 处理模型和文件，获取图像处理路径和模型信息
    @staticmethod
    def process_model_and_file(model_id, uploaded_file):
        try:
            try:
                model_id = int(model_id)
            except ValueError:
                raise ValidationError("model_id 应该是整数类型")

            # 检查 model_id 是否有效
            ModelService.get_model_by_id(model_id)

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
        except ValidationError as ve:
            logger.error(f"Validation error: {str(ve)}")
            raise ve
        except FileUploadError as fe:
            logger.error(f"File upload error: {str(fe)}")
            raise fe
        except ImageProcessingError as ie:
            logger.error(f"Image processing error: {str(ie)}")
            raise ie
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise e

    @staticmethod
    def get_model_accuracy(model_id: int, dataset_id: int) -> dict:

        try:
            if not model_id or not dataset_id:
                raise ValidationError("Model ID and Dataset ID are required")

            model = ModelService.get_model_by_id(model_id)
            dataset = DatasetService.get_dataset_by_id(dataset_id)

            accuracy = ((model_id * dataset_id) % 100) / 100  # 模拟准确率，实际应用中应使用模型的真实准确率
            return {
                "data": {
                    "model_id": model_id,
                    "dataset_id": dataset_id,
                    "accuracy": accuracy
                }
            }
        except ValidationError as ve:
            logger.error(f"Validation error: {ve.message}")
            raise ve
        except NotFoundError as ne:
            logger.error(f"Model with ID {model_id} not found: {str(ne)}")
            raise ne
        except Exception as e:
            logger.error(f"Database error occurred while retrieving model accuracy: {str(e)}")
            raise e
