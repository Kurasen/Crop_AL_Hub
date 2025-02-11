import re

from app.exception.errors import ValidationError
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
    def search(name=None, path=None, description=None,type=None, stars=None,
               page=1, per_page=10, sort_by='accuracy', sort_order='asc'):
        """支持多条件查询"""
        query = Dataset.query

        # 模糊查询数据集名称
        if name:
            query = query.filter(Dataset.name.ilike(f"%{name}%"))

        # 模糊查询数据集路径
        if path:
            query = query.filter(Dataset.path.ilike(f"%{path}%"))

        # 添加描述字段的查询条件
        if description:
            query = query.filter(Dataset.description.ilike(f"%{description}%"))

        # 精确查询多个标签（支持多标签模糊查询）
        if type:
            # 检测非法字符（仅允许汉字、英文字母、数字、空格、逗号、分号）
            if re.search(r"[^\u4e00-\u9fa5,，; ；]", type):
                raise ValidationError("Invalid type input. Only Chinese characters, spaces, commas, and semicolons "
                                      "are allowed.")

            # 使用正则表达式分割，支持 逗号 `,`、分号 `;`、空格 ` ` 作为分隔符
            tags = re.split(r'[,\s;，；]+', type)
            tags = [tag.strip() for tag in tags if tag.strip()]  # 去除空格并过滤空标签

            # 遍历所有标签，确保查询的 `type` 字段包含每个输入的标签
            for tag in tags:
                query = query.filter(Dataset.type.ilike(f"%{tag}%"))

        # 精确查询星级
        if stars is not None:
            query = query.filter(Dataset.stars == stars)  # 新字段

        if sort_by in ['stars', 'likes']:
            if sort_order == 'desc':
                query = query.order_by(getattr(Dataset, sort_by).desc())  # 降序
            else:
                query = query.order_by(getattr(Dataset, sort_by).asc())  # 升序
        else:
            raise ValidationError("Invalid sort field. Only 'stars', and 'likes' are allowed.")

        # 计算总数
        total_count = query.count()

        # 分页查询
        datasets = query.offset((page - 1) * per_page).limit(per_page).all()

        print(f"SQL Query: {str(query)}")
        return total_count, datasets
