from app.exts import db

from enum import Enum as PyEnum

from app.interface.user_interaction_base import UserInteractionBase


class OrderType(PyEnum):
    MODEL = "model"
    DATASET = "dataset"


class OrderStatus(PyEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Order(UserInteractionBase):
    __tablename__ = 'orders_table'
    # __table_args__ = (
    #     # 唯一性约束
    #     db.UniqueConstraint('user_id', 'model_id', name='uq_user_model'),
    #     db.UniqueConstraint('user_id', 'dataset_id', name='uq_user_dataset'),
    #
    #     # # 互斥性约束
    #     # db.CheckConstraint(
    #     #     "(model_id IS NOT NULL AND dataset_id IS NULL) OR (model_id IS NULL AND dataset_id IS NOT NULL)",
    #     #     name="chk_mutual_exclusion_model_dataset"
    #     # )
    # )
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_type = db.Column(db.Enum(OrderType), nullable=False)
    order_date = db.Column(db.DateTime(timezone=True),
                           server_default=db.func.now(),
                           comment="订单创建时间")
    status = db.Column(db.Enum(OrderStatus), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)

    # 关系定义
    # user = db.relationship("User", back_populates="orders", lazy="joined")
    # model = db.relationship("Model", back_populates="orders", lazy="select")
    # dataset = db.relationship("Dataset", back_populates="orders", lazy="select")

    def __repr__(self):
        return f"<Order(id={self.id}, type={self.order_type}, price={self.price})>"
