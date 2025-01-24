# 数据库模型：Dataset
from app.exts import db


class Dataset(db.Model):
    __tablename__ = 'dataset_table'  # 数据库表名

    id = db.Column(db.Integer, primary_key=True)  # 主键
    name = db.Column(db.String(100), nullable=False)  # 数据集名称
    path = db.Column(db.String(255), nullable=False)  # 数据集文件路径
    size = db.Column(db.String(50), nullable=False)  # 数据集大小 (例如 MB 或 GB)
    describe = db.Column(db.String(255), nullable=True)  # 数据集描述
    cuda = db.Column(db.Boolean, nullable=False)  # 是否支持 CUDA，布尔值

    def __repr__(self):
        return f"<Dataset {self.name}>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "path": self.path,
            "size": self.size,
            "describe": self.describe,
            "cuda": bool(self.cuda)  # 将 0/1 转换为 True/False
        }
