from app import Dataset
from app.core.exception import DatabaseError, NotFoundError, logger
from app.dataset.dataset_repo import DatasetRepository
from app.exts import db
from app.utils.common.json_encoder import ResponseBuilder


class DatasetService:
    @staticmethod
    def get_all_datasets():
        """获取所有数据集"""
        datasets = DatasetRepository.get_all_datasets()
        if not datasets:
            raise DatabaseError("未查询到数据")
        return [DatasetService._convert_to_dict(dataset) for dataset in datasets]

    @staticmethod
    def get_dataset_by_id(dataset_id: int):
        # 获取指定ID的模型
        dataset = DatasetRepository.get_dataset_by_id(dataset_id)
        if not dataset:
            raise NotFoundError("数据集未找到")
        return dataset

    @staticmethod
    def search_datasets(search_params: dict):
        """根据过滤条件获取数据集"""

        # 统一分页参数处理
        page = max(1, int(search_params.get("page", 1)))
        per_page = min(100, max(1, int(search_params.get("per_page", 5))))

        total_count, datasets = DatasetRepository.search(
            search_params,
            page=page,
            per_page=per_page
        )

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

        # 构建返回数据
        items = [DatasetService._convert_to_dict(dataset) for dataset in datasets]
        response_data = ResponseBuilder.paginated_response(
            items=items,
            total_count=total_count,
            page=page,
            per_page=per_page
        )

        return response_data, 200

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
            logger.error(f"Error occurred while creating model: {str(e)}")
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
            logger.error(f"Error updating dataset: {str(e)}")
            raise

    @staticmethod
    def delete_dataset(instance: Dataset):
        """删除模型"""
        try:
            # 获取模型对象
            dataset = DatasetService.get_dataset_by_id(instance)

            DatasetRepository.delete_dataset(dataset)

            db.session.commit()
            return {"message": "数据删除成功"}, 204
        except NotFoundError as ne:
            logger.error(f"Dataset with ID {instance.id} not found: {str(ne)}")
            raise ne
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error occurred while deleting model {instance}: {str(e)}")
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
