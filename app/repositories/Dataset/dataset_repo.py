from app.models.dataset import Dataset


class DatasetRepository:
    @staticmethod
    def get_all():
        """获取所有数据集"""
        return Dataset.query.all()

    @staticmethod
    def get_by_id(dataset_id):
        """通过ID获取单个数据集"""
        return Dataset.query.get(dataset_id)

    @staticmethod
    def get_by_name(name: str):
        """根据数据集名称查询"""
        return Dataset.query.filter(Dataset.name.ilike(f"%{name}%")).all()

    @staticmethod
    def get_by_path(path: str):
        """根据路径查询数据集"""
        return Dataset.query.filter(Dataset.path.ilike(f"%{path}%")).all()

    @staticmethod
    def get_by_cuda(cuda: bool):
        """根据是否支持CUDA查询数据集"""
        return Dataset.query.filter_by(cuda=cuda).all()

    @staticmethod
    def search(name=None, path=None, cuda=None, size_range=None, describe=None):
        """支持多条件查询"""
        query = Dataset.query

        # 模糊查询数据集名称
        if name:
            query = query.filter(Dataset.name.ilike(f"%{name}%"))

        # 模糊查询数据集路径
        if path:
            query = query.filter(Dataset.path.ilike(f"%{path}%"))

        # 精确查询CUDA支持
        if cuda is not None:
            query = query.filter(Dataset.cuda == cuda)

        # 添加描述字段的查询条件
        if describe:
            query = query.filter(Dataset.describe.ilike(f"%{describe}%"))

        print(f"SQL Query: {str(query)}")
        return query.all()
