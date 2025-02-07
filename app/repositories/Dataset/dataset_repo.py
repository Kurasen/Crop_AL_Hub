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

        # 查询数据集大小范围（处理大小字段转换）
        if size_range:
            print(f"size_range: {size_range}")
            size_min, size_max = size_range

            # 转换 size_min 和 size_max 为字节
            try:
                if size_min != '∞':
                    min_size_value = DatasetRepository._convert_size_to_bytes(size_min)
                else:
                    min_size_value = 0  # 无下限
                max_size_value = DatasetRepository._convert_size_to_bytes(size_max)
                if size_max != '∞':
                    max_size_value = DatasetRepository._convert_size_to_bytes(size_max)
                else:
                    max_size_value = float('inf')  # 无上限
            except ValueError as e:
                # 如果出现转换错误，可以返回一个错误响应
                raise ValueError(f"Invalid size format: {e}")

            # 首先获取所有数据集的大小，然后在 Python 中过滤
            datasets = query.all()
            filtered_datasets = [
                dataset for dataset in datasets
                if min_size_value <= DatasetRepository._convert_size_to_bytes(dataset.size) <= max_size_value
            ]
            return filtered_datasets

        return query.all()

    @staticmethod
    def _convert_size_to_bytes(size_str):
        # 如果是 '∞' 或 '0'，直接返回特殊值
        if size_str == '∞':
            return float('inf')  # 表示没有上限
        if size_str == '0':
            return 0  # 表示没有下限

        # 先检查 size_str 是否为空
        if not size_str:
            return 0

        # 确保 size_str 是字符串类型并进行清理
        size_str = str(size_str).strip().upper()  # 转为字符串后处理

        # 检查 size_str 是否包含无效字符（如 'DATASET.SIZE'）
        if not any(char.isdigit() for char in size_str):  # 如果没有数字，说明可能是无效字符串
            raise ValueError(f"Invalid size format: {size_str}. Expected format like '100MB' or '1GB'.")

        # 确保 size_str 末尾包含有效的单位
        if not size_str[-2:].isalpha():  # 检查最后两位是否是字母（单位）
            raise ValueError(f"Invalid unit in size: {size_str}. Expected format like '100MB' or '1GB'.")

        # 处理大小字符串，假设它是类似于 '100MB' 或 '1GB' 格式
        try:
            size_value = float(size_str[:-2])  # 获取数字部分
        except ValueError:
            raise ValueError(f"Invalid number in size: {size_str}")

        size_unit = size_str[-2:]  # 获取单位部分

        if size_unit == 'MB':
            return size_value * 1024 * 1024  # MB 转为字节
        elif size_unit == 'GB':
            return size_value * 1024 * 1024 * 1024  # GB 转为字节
        elif size_unit == 'KB':
            return size_value * 1024  # KB 转为字节
        else:
            raise ValueError(f"Unknown size unit: {size_unit}. Expected 'MB', 'GB', or 'KB'.")
