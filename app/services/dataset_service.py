from app.exception.errors import DatabaseError
from app.repositories.Dataset.dataset_repo import DatasetRepository


class DatasetService:
    @staticmethod
    def get_all_datasets():
        """获取所有数据集"""
        datasets = DatasetRepository.get_all()
        if not datasets:
            raise DatabaseError("No datasets found.")
        return [DatasetService._convert_to_dict(dataset) for dataset in datasets]

    @staticmethod
    def search_datasets(name=None, path=None, size_min=None, size_max=None, description=None,
                        type=None, stars=None, sort_by='accuracy', sort_order='asc', page=1, per_page=5):
        """根据过滤条件获取数据集"""
        # 打印转换后的大小值
        #print(f"Converted sizes: min_size={min_size_value}, max_size={max_size_value}")
        total_count, datasets = DatasetRepository.search(
            name=name,
            path=path,
            description=description,
            type=type,
            stars=stars,
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
