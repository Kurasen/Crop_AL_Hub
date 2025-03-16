from flask import current_app

from app.core.exception import DatabaseError, NotFoundError
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
    def search_datasets(search_params: dict):
        """根据过滤条件获取数据集"""

        total_count, datasets = DatasetRepository.search(search_params)

        # 转换大小为字节（None 代表不限制）
        min_size_value = DatasetRepository.convert_size_to_bytes(search_params.get('size_min')) if search_params.get(
            'size_min') else None
        max_size_value = DatasetRepository.convert_size_to_bytes(search_params.get('size_max')) if search_params.get(
            'size_max') else None

        if search_params.get('size_min') or search_params.get('size_max'):
            datasets = [
                dataset for dataset in datasets
                if DatasetService._is_size_in_range(dataset.size, min_size_value, max_size_value)
            ]

        # 将结果转换为字典格式并返回
        return {
            "data": {
                "items": [DatasetService._convert_to_dict(dataset) for dataset in datasets],
                "total": total_count,
                "page": search_params.get("page", 1),
                "per_page": search_params.get("per_page", 5),
                "total_pages": (total_count + search_params.get("per_page", 5) - 1) // search_params.get("per_page", 5)  # 计算总页数
            },
        }, 200

    @staticmethod
    def create_dataset(dataset_instance):
        """
        在数据库中创建一个新的数据集
        :return: 创建的数据集对象
        """
        try:
            DatasetRepository.save_dataset(dataset_instance)
            db.session.commit()
            return dataset_instance.to_dict(), 201
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error occurred while creating model: {str(e)}")
            raise e

    @staticmethod
    def update_dataset(dataset_instance):
        """
        更新指定数据集的信息
        :param dataset_instance:
        :return: 更新后的数据集对象
        """
        try:
            DatasetRepository.save_dataset(dataset_instance)
            db.session.commit()
            return dataset_instance.to_dict(), 200
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating dataset: {str(e)}")
            raise

    @staticmethod
    def delete_dataset(dataset_id):
        """删除模型"""
        try:
            # 获取模型对象
            dataset = DatasetService.get_dataset_by_id(dataset_id)

            DatasetRepository.delete_dataset(dataset)

            db.session.commit()
            return {"message": "Dataset deleted successfully"}, 204
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
