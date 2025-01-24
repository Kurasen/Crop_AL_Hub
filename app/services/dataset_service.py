from app.repositories.dataset_repo import DatasetRepository

class DatasetService:
    @staticmethod
    def get_all_datasets():
        """获取所有数据集"""
        datasets = DatasetRepository.get_all()
        return [dataset.to_dict() for dataset in datasets]

    @staticmethod
    def get_datasets(name=None, path=None, cuda=None, size_range=None):
        """根据过滤条件获取数据集"""
        datasets = DatasetRepository.search(name=name, path=path, cuda=cuda, size_range=size_range)
        return [dataset.to_dict() for dataset in datasets]
