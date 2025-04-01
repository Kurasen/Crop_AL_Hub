from datetime import datetime

from sqlalchemy import JSON

from app.exts import db


class Task(db.Model):
    __tablename__ = 'task_table'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    app_id = db.Column(db.String(20), nullable=False)
    models_ids = db.Column(JSON, nullable=True)  # 存储数组格式的JSON数据
    image_path = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False)
    remarks = db.Column(db.Text, nullable=True)
    creates_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    result_info = db.Column(db.JSON, nullable=True)

    def __repr__(self):
        return f"<Task {self.name}>"

    def __init__(self, **kwargs):
        """
        :param kwargs: 数据集的各个字段参数
        """
        # 使用父类的初始化方法来处理字段初始化
        super().__init__(**kwargs)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "app_id": self.app_id,
            "models_ids": self.models_ids,
            "image_path": self.image_path,
            "status": self.status,
            "remarks": self.remarks,
            "creates_at": self.creates_at,
            "updated_at": self.updated_at,
            "result_info": self.result_info
        }