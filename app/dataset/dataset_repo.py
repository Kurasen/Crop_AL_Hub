
from app.utils.tag_filtering_utils import process_and_filter_tags
from app.core.exception import InvalidSizeError, ValidationError
from app.exts import db
from app.dataset.dataset import Dataset

# 定义排序字段的枚举类型
SORT_BY_CHOICES = ['stars', 'likes', 'downloads']


class DatasetRepository:
    @staticmethod
    def get_all():
        """获取所有数据集"""
        return Dataset.query.all()

    @staticmethod
    def get_dataset_by_id(dataset_id: int):
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
    def search(params: dict):
        """支持多条件查询"""
        query = Dataset.query

        # 模糊查询数据集名称
        if params.get('name'):
            query = query.filter(Dataset.name.ilike(f"%{params.get('name')}%"))

        # 添加描述字段的查询条件
        if params.get('description'):
            query = query.filter(Dataset.description.ilike(f"%{params.get('description')}%"))

        # 精确查询多个标签（支持多标签模糊查询）
        if params.get('type'):
            query = process_and_filter_tags(query, Dataset.type, params.get('type'))

            # 根据 sort_by 和 sort_order 排序
        if params.get('sort_by') in SORT_BY_CHOICES:
            if params.get('sort_order') == 'desc':
                query = query.order_by(getattr(Dataset, params.get('sort_by')).desc(), Dataset.id.asc())
            else:
                query = query.order_by(getattr(Dataset, params.get('sort_by')).asc(), Dataset.id.asc())
        elif params.get('sort_by') == 'size':
            # 获取所有数据集
            datasets = query.all()

            # 进行大小转换和排序
            datasets.sort(key=lambda dataset: DatasetRepository.convert_size_to_bytes(dataset.size),
                          reverse=(params.get('sort_order') == 'desc'))

            # 返回排序后的数据集
            return len(datasets), datasets
        elif not params.get("page", 1) and not params.get('sort_order', 5):
            pass

        # 计算总数
        total_count = query.count()

        # 分页查询
        datasets = query.offset((params.get('page', 1) - 1) * params.get('per_page', 5)).limit(params.get('per_page', 5)).all()

        print(f"SQL Query: {str(query)}")
        return total_count, datasets

    @staticmethod
    def convert_size_to_bytes(size_str):
        """将 100MB, 1GB 转换为字节数"""
        if not size_str:
            raise InvalidSizeError(size_str, "Size string cannot be empty")
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
    def save_dataset(dataset_instance):
        """通用保存方法，用于创建和更新"""
        db.session.add(dataset_instance)
        return dataset_instance

    @staticmethod
    def delete_dataset(dataset):
        """删除数据集"""
        db.session.delete(dataset)
