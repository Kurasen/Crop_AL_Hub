from sqlalchemy import CheckConstraint
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
    # __table_args__ = (
    #     db.UniqueConstraint('user_id', 'model_id', name='uq_user_model'),
    #     db.UniqueConstraint('user_id', 'dataset_id', name='uq_user_dataset'),
    #     CheckConstraint(
    #         "(star_type = 'MODEL' AND model_id IS NOT NULL AND dataset_id IS NULL) OR "
    #         "(star_type = 'DATASET' AND dataset_id IS NOT NULL AND model_id IS NULL)",
    #         name='ck_star_type_consistency'
    #     )
    # )
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    star_type = db.Column(db.Enum(StarType), nullable=False)

    # 双向关系:限制反向关系加载策略(避免N+1查询)
    #user = db.relationship("User", back_populates="stars", lazy="joined")
    #model = db.relationship("Model", back_populates="stars", lazy="select")
    #dataset = db.relationship("Dataset", back_populates="stars", lazy="select")

    def __repr__(self):
        return f"<Star(id={self.id}, star_type={self.star_type}, user_id={self.user_id})>"

