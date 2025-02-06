from app.repositories.Dataset.dataset_repo import DatasetRepository


class DatasetService:
    @staticmethod
    def get_all_datasets():
        """获取所有数据集"""
        try:
            datasets = DatasetRepository.get_all()
            return [dataset.to_dict() for dataset in datasets]  # 转换为字典格式
        except Exception as e:
            # 捕获所有异常，记录日志并返回错误信息
            print(f"Error fetching all datasets: {e}")
            return {"error": "An error occurred while fetching datasets."}

    @staticmethod
    def get_datasets(name=None, path=None, cuda=None, size_range=None):
        """根据过滤条件获取数据集"""
        try:
            datasets = DatasetRepository.search(name=name, path=path, cuda=cuda, size_range=size_range)
            return [dataset.to_dict() for dataset in datasets]  # 转换为字典格式
        except ValueError as e:
            # 捕获尺寸转换错误并返回有意义的错误消息
            return {"error": f"Invalid size format: {e}"}
        except Exception as e:
            print(f"Error fetching datasets: {e}")
            return {"error": "An error occurred while fetching datasets."}
