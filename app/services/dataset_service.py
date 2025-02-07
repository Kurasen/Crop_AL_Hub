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

    def get_datasets(name=None, path=None, cuda=None, size_min=None, size_max=None, describe=None):

        """根据过滤条件获取数据集"""
        # 转换大小为字节（None 代表不限制）
        min_size_value = DatasetService._convert_size_to_bytes(size_min) if size_min else None
        max_size_value = DatasetService._convert_size_to_bytes(size_max) if size_max else None

        # 打印转换后的大小值
        print(f"Converted sizes: min_size={min_size_value}, max_size={max_size_value}")
        datasets = DatasetRepository.search(
            name=name, path=path, cuda=cuda, size_range=(min_size_value, max_size_value), describe=describe
        )

        if size_min or size_max:
            datasets = [
                dataset for dataset in datasets
                if DatasetService._is_size_in_range(dataset.size, min_size_value, max_size_value)
            ]

        # 不抛异常，返回空列表
        return [DatasetService._convert_to_dict(dataset) for dataset in datasets]

    @staticmethod
    def _convert_to_dict(dataset):
        """将数据集转换为字典格式"""
        # 假设 dataset 是一个模型对象，转换为字典
        return dataset.to_dict()  # 假设你有一个 to_dict 方法

    @staticmethod
    def _convert_size_to_bytes(size_str):
        """将 100MB, 1GB 转换为字节数"""
        if not size_str:
            return None
        size_str = str(size_str).strip().upper()

        size_units = {"KB": 1024, "MB": 1024 ** 2, "GB": 1024 ** 3}
        for unit in size_units:
            if size_str.endswith(unit):
                try:
                    size_value = float(size_str[:-len(unit)])  # 提取数值部分
                    return int(size_value * size_units[unit])  # 转换为字节
                except ValueError:
                    raise ValueError(f"Invalid number in size: {size_str}")

        raise ValueError(f"Unknown size unit in: {size_str}. Use KB, MB, GB.")

    @staticmethod
    def _is_size_in_range(size_str, min_size, max_size):
        """判断数据集大小是否在范围内"""
        if not size_str:
            return False

        # 将 size_str 转换为字节数
        dataset_size_bytes = DatasetService._convert_size_to_bytes(size_str)

        # 判断是否在范围内
        if min_size is not None and dataset_size_bytes < min_size:
            return False
        if max_size is not None and dataset_size_bytes > max_size:
            return False
        return True
