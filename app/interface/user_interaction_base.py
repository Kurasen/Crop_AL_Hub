
from app.exts import db


class UserInteractionBase(db.Model):
    """所有用户交互模型的公共字段基类"""
    __abstract__ = True  # 不会创建实际表

    user_id = db.Column(db.Integer, db.ForeignKey('user_table.id'), nullable=False)
    model_id = db.Column(db.Integer, db.ForeignKey('model_table.id'), nullable=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey('dataset_table.id'), nullable=True)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())
