from sqlalchemy.ext.hybrid import hybrid_property

from app.exts import db
from enum import Enum as PyEnum

from app.interface.user_interaction_base import UserInteractionBase


# 定义收藏类型枚举
class StarType(PyEnum):
    MODEL = "model"
    DATASET = "dataset"


class Star(UserInteractionBase):
    __tablename__ = 'stars_table'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'model_id', name='uq_user_model'),
        db.UniqueConstraint('user_id', 'dataset_id', name='uq_user_dataset')
    )
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    star_type = db.Column(db.Enum(StarType), nullable=False)
    star_date = db.Column(db.DateTime(timezone=True),
                          server_default=db.func.now(),
                          comment="收藏时间")

    # 双向关系定义
    user = db.relationship("User", back_populates="stars")
    model = db.relationship("Model", back_populates="stars")
    dataset = db.relationship("Dataset", back_populates="stars")

    def __repr__(self):
        return f"<Star(id={self.id}, type={self.star_type}, user={self.user_id})>"

