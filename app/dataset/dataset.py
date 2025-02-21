# 数据库模型：Dataset

from app.exts import db


class Dataset(db.Model):
    __tablename__ = 'dataset_table'  # 数据库表名

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # 主键
    name = db.Column(db.String(100), nullable=False, index=True)  # 数据集名称
    path = db.Column(db.String(255), default="")  # 数据集文件路径
    size = db.Column(db.String(50), default="")  # 数据集大小 (例如 MB 或 GB)
    description = db.Column(db.Text, default="")  # 数据集描述
    type = db.Column(db.String(100), default="")  # 数据集类型
    downloads = db.Column(db.Integer, default=0)  # 下载次数
    stars = db.Column(db.Integer, default=0)  # 收藏数
    likes = db.Column(db.Integer, default=0)  # 点赞数

    def __init__(self, **kwargs):
        """
        :param kwargs: 数据集的各个字段参数
        """
        # 使用父类的初始化方法来处理字段初始化
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<Dataset {self.name}>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "path": self.path,
            "size": self.size,
            "description": self.description,
            "type": self.type,
            "downloads": self.downloads,
            "stars": self.stars,
            "likes": self.likes
        }
