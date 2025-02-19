from flask import current_app

from app.core.exception import DatabaseError, ValidationError, NotFoundError
from app.dataset.dataset_repo import DatasetRepository
from app.exts import db


class DatasetService:
    @staticmethod
    def get_all_datasets():
        """获取所有数据集"""
        datasets = DatasetRepository.get_all()
        if not datasets:
            raise DatabaseError("No datasets found.")
        return [DatasetService._convert_to_dict(dataset) for dataset in datasets]

    @staticmethod
    def get_dataset_by_id(dataset_id: int):
        # 获取指定ID的模型
        dataset = DatasetRepository.get_dataset_by_id(dataset_id)
        if not dataset:
            raise NotFoundError(f"Dataset with ID {dataset_id} not found")

        return dataset

    @staticmethod
    def search_datasets(name=None, path=None, size_min=None, size_max=None, description=None,
                        type=None, sort_by=None, sort_order=None, page=1, per_page=5):
        """根据过滤条件获取数据集"""
        total_count, datasets = DatasetRepository.search(
            name=name,
            path=path,
            description=description,
            type=type,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            per_page=per_page
        )

        # 转换大小为字节（None 代表不限制）
        min_size_value = DatasetRepository.convert_size_to_bytes(size_min) if size_min else None
        max_size_value = DatasetRepository.convert_size_to_bytes(size_max) if size_max else None

        if size_min or size_max:
            datasets = [
                dataset for dataset in datasets
                if DatasetService._is_size_in_range(dataset.size, min_size_value, max_size_value)
            ]

        # 将结果转换为字典格式并返回
        return {
            "data": [DatasetService._convert_to_dict(dataset) for dataset in datasets],
            "total_count": total_count,
            "page": page,
            "per_page": per_page,
            "total_pages": (total_count + per_page - 1) // per_page  # 计算总页数
        }

    @staticmethod
    def create_dataset(data):
        """
        在数据库中创建一个新的数据集
        :param data: 数据字典，包含数据集的相关信息
        :return: 创建的数据集对象
        """
        try:
            # 进行数据验证（如果需要）
            if not data.get("name"):
                raise ValidationError("Dataset name is required.")

            dataset = DatasetRepository.create_dataset(data)
            db.session.commit()
            return dataset.to_dict(), 201
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error occurred while creating model: {str(e)}")
            raise e

    @staticmethod
    def update_dataset(dataset_id, updates):
        """
        更新指定数据集的信息
        :param dataset_id: 数据集 ID
        :param updates: 需要更新的字段和值
        :return: 更新后的数据集对象
        """
        try:
            dataset = DatasetService.get_dataset_by_id(dataset_id)
            if not dataset:
                raise NotFoundError(f"Dataset with ID {dataset_id} not found.")
            updated_dataset = DatasetRepository.update_dataset(dataset, **updates)
            db.session.commit()
            return updated_dataset.to_dict(), 201
        except NotFoundError as ne:
            current_app.logger.error(f"Validation error while updating model {dataset_id}: {str(ne)}")
            raise ne
        except Exception as e:
            db.session.rollback()  # 回滚事务
            current_app.logger.error(f"Unexpected error while updating model {dataset_id}: {str(e)}")
            raise e

    @staticmethod
    def delete_dataset(dataset_id):
        """删除模型"""
        try:
            # 获取模型对象
            dataset = DatasetService.get_dataset_by_id(dataset_id)

            DatasetRepository.delete_dataset(dataset)

            db.session.commit()
            return {"message": "Dataset deleted successfully"}, 200
        except NotFoundError as ne:
            current_app.logger.error(f"Dataset with ID {dataset_id} not found: {str(ne)}")
            raise ne
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error occurred while deleting model {dataset_id}: {str(e)}")
            raise e

    @staticmethod
    def _convert_to_dict(dataset):
        """将数据集转换为字典格式"""
        # 假设 dataset 是一个模型对象，转换为字典
        return dataset.to_dict()  # 假设你有一个 to_dict 方法

    @staticmethod
    def _is_size_in_range(size_str, min_size, max_size):
        """判断数据集大小是否在范围内"""
        if not size_str:
            return False

        # 将 size_str 转换为字节数
        dataset_size_bytes = DatasetRepository.convert_size_to_bytes(size_str)

        # 判断是否在范围内
        if min_size is not None and dataset_size_bytes < min_size:
            return False
        if max_size is not None and dataset_size_bytes > max_size:
            return False
        return True
