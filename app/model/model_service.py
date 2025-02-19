from flask import current_app

from app.utils.upload_file import save_uploaded_file
from app.utils.Validator import Validator
from app.core.exception import DatabaseError, ValidationError, FileUploadError, ImageProcessingError, \
    NotFoundError
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
            raise NotFoundError(f"Dataset with ID {model_id} not found")
        return model

    @staticmethod
    def search_models(name=None, input=None, cuda=None, description=None, type=None, page=1, per_page=10,
                      sort_by='accuracy', sort_order='asc'):
        """查询模型，调用Repository层"""
        try:
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
        except Exception as e:
            current_app.logger.error(f"Error occurred while searching models: {str(e)}")
            raise e

    @staticmethod
    def create_model(data):
        """创建模型"""
        try:
            # 校验数据是否合法
            validator = Validator()
            validator.required(
                fields=["name", "input", "instruction"],
                custom_messages={  # 确保键名与字段名完全一致
                    "name": "名称不能为空",
                    "input": "输入图片类型不能为空",
                    "instruction": "命令不能为空"
                }
            )
            validator.validate(data)
            model = ModelRepository.create_model(data)
            db.session.commit()
            return model.to_dict(), 201
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error occurred while creating model: {str(e)}")
            raise e

    @staticmethod
    def update_model(model_id, updates):
        """更新模型"""
        try:
            # 获取模型对象
            model = ModelService.get_model_by_id(model_id)
            if not model:
                raise NotFoundError(f"Model with ID {model_id} not found")

            updated_model = ModelRepository.update_model(model, **updates)
            db.session.commit()
            return updated_model.to_dict(), 200
        except NotFoundError as ne:
            current_app.logger.error(f"Validation error while updating model {model_id}: {str(ne)}")
            raise ne
        except Exception as e:
            db.session.rollback()  # 回滚事务
            current_app.logger.error(f"Unexpected error while updating model {model_id}: {str(e)}")
            raise e

    @staticmethod
    def delete_model(model_id):
        """删除模型"""
        try:
            model = ModelRepository.get_model_by_id(model_id)
            if not model:
                raise NotFoundError(f"Model with ID {model_id} not found")

            ModelRepository.delete_model(model)

            db.session.commit()
            return {"message": "Model deleted successfully"}, 200

        except NotFoundError as ne:
            current_app.logger.error(f"Model with ID {model_id} not found: {str(ne)}")
            raise ne
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error occurred while deleting model {model_id}: {str(e)}")
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
        except ValidationError as ve:
            current_app.logger.error(f"Validation error: {str(ve)}")
            raise ve
        except FileUploadError as fe:
            current_app.logger.error(f"File upload error: {str(fe)}")
            raise fe
        except ImageProcessingError as ie:
            current_app.logger.error(f"Image processing error: {str(ie)}")
            raise ie
        except Exception as e:
            current_app.logger.error(f"Unexpected error: {str(e)}")
            raise e

    @staticmethod
    def get_model_accuracy(model_id: int, dataset_id: int) -> dict:

        try:
            if not model_id or not dataset_id:
                raise ValidationError("Model ID and Dataset ID are required")

            model = ModelService.get_model_by_id(model_id)
            dataset = DatasetService.get_dataset_by_id(dataset_id)

            # 校验模型和数据集是否存在
            if not model:
                raise NotFoundError(f"Model with ID {model_id} not found")
            if not dataset:
                raise NotFoundError(f"Dataset with ID {dataset_id} not found")

            accuracy = ((model_id * dataset_id) % 100) / 100 # 模拟准确率，实际应用中应使用模型的真实准确率
            return {
                "model_id": model_id,
                "dataset_id": dataset_id,
                "accuracy": accuracy
            }
        except ValidationError as ve:
            current_app.logger.error(f"Validation error: {ve.message}")
            raise ve
        except NotFoundError as ne:
            current_app.logger.error(f"Model with ID {model_id} not found: {str(ne)}")
            raise ne
        except Exception as e:
            current_app.logger.error(f"Database error occurred while retrieving model accuracy: {str(e)}")
            raise e
