# 数据库模型：Dataset
from app.exts import db


class Dataset(db.Model):
    __tablename__ = 'dataset_table'  # 数据库表名

    id = db.Column(db.Integer, primary_key=True)  # 主键
    name = db.Column(db.String(100), nullable=False)  # 数据集名称
    path = db.Column(db.String(255), nullable=False)  # 数据集文件路径
    size = db.Column(db.String(50), nullable=False)  # 数据集大小 (例如 MB 或 GB)
    description = db.Column(db.Text, nullable=True)  # 数据集描述
    type = db.Column(db.String(100), nullable=True)  # 新增字段：数据集类型
    downloads = db.Column(db.Integer, nullable=False, default=0)  # 新增字段：下载次数
    stars = db.Column(db.Integer, nullable=False, default=0)  # 星级
    likes = db.Column(db.Integer, nullable=False, default=0)  # 点赞数

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
