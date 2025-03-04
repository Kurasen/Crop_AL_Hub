# 数据库模型：Dataset
from datetime import timedelta

from sqlalchemy.ext.hybrid import hybrid_property

from app.core.redis_connection_pool import redis_pool
from app.exts import db
from app.order.order import OrderStatus, Order


class Dataset(db.Model):
    __tablename__ = 'dataset_table'  # 数据库表名

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # 主键
    name = db.Column(db.String(100), nullable=False, index=True)  # 数据集名称
    path = db.Column(db.String(255))  # 数据集文件路径
    size = db.Column(db.String(50))  # 数据集大小 (例如 MB 或 GB)
    description = db.Column(db.Text)  # 数据集描述
    type = db.Column(db.String(100))  # 数据集类型
    likes = db.Column(db.Integer, default=0)  # 点赞数
    price = db.Column(db.Numeric(10, 2))

    # stars = db.relationship("Star", back_populates="dataset", lazy="dynamic")
    # orders = db.relationship("Order", back_populates="dataset", lazy="dynamic")

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
            # "stars": self.stars,
            "likes": self.likes
        }

    @hybrid_property
    def sales_count(self):
        """实时销售计数（带缓存）"""
        cache_key = f"dataset_sales:{self.id}"
        if cached := redis_pool.get(cache_key):
            return int(cached)

        count = self.orders.filter_by(
            status=OrderStatus.COMPLETED
        ).count()

        redis_pool.setex(cache_key, timedelta(minutes=5), count)
        return count

    @sales_count.expression
    def sales_count(cls):
        """SQL表达式（用于查询和排序）"""
        from sqlalchemy import select, func
        return select([func.count(Order.id)]).where(
            (Order.model_id == cls.id) &
            (Order.status == OrderStatus.COMPLETED)
        ).label("sales_count")
