from sqlalchemy.ext.hybrid import hybrid_property

from app import Star
from app.exts import db
from app.order.order import OrderStatus
from datetime import datetime

from app.utils.image_url_utils import ImageURLHandlerUtils

"""
    graph TD
    A[Model 模型层] -->|定义 hybrid_property| B(ORM 查询能力)
    C[Service 服务层] -->|处理缓存| D(Redis 连接池)
    A -->|被 Service 调用| C
    B -->|生成高效SQL| E[数据库]
    D -->|缓存加速| F[高并发访问]
    """


# 定义数据库模型
class Model(db.Model):
    __tablename__ = 'model_table'
    __table_args__ = (
        db.Index('idx_created_at', 'created_at'),
        db.Index('idx_updated_at', 'updated_at'),
        db.Index('idx_likes', 'likes'),
        db.Index('idx_accuracy', 'accuracy'),
        # 时间约束
        db.CheckConstraint(
            "created_at <= updated_at OR updated_at IS NULL",
            name='time_check'
        ),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # 主键
    name = db.Column(db.String(100), nullable=False, index=True)  # 模型名称
    image = db.Column(db.String(255), default="")  # 模型图片路径，长度改为 255
    input = db.Column(db.String(100), default="")  # 输入类型
    description = db.Column(db.Text, default="")  # 描述字段改为 Text 类型
    cuda = db.Column(db.Boolean, default=False)  # 是否支持 CUDA，默认 False
    instruction = db.Column(db.Text, default="")
    output = db.Column(db.String(100), default="")  # 输出字段
    accuracy = db.Column(db.Numeric(4, 2), default=0)  # 精度字段，DECIMAL(4, 2) 对应 Numeric(4, 2)
    icon = db.Column(db.String(255), nullable=True, default=None)
    type = db.Column(db.String(100), default="")  # 模型类型
    likes = db.Column(db.Integer, default=0)  # 点赞数字段
    # price = db.Column(db.Numeric(10, 2))
    user_id = db.Column(db.Integer, db.ForeignKey('user_table.id'), nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # 创建时间字段，默认当前时间
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    readme = db.Column(db.Text, default="")

    # 定义反向关系（属性名必须与 User.models 的 back_populates 一致）
    user = db.relationship("User", back_populates="models")

    # stars = db.relationship("Star", back_populates="model", lazy="dynamic")
    # orders = db.relationship("Order", back_populates="model", lazy="dynamic")

    def __init__(self, **kwargs):
        """
        :param kwargs: 模型的各个字段参数
        """
        # 使用父类的初始化方法来处理字段初始化
        super().__init__(**kwargs)

    def __repr__(self):
        return f'<Model {self.name}>'

    def to_dict(self):
        base_data = {
            'id': self.id,
            'name': self.name,
            'image': self.image,
            'input': self.input,
            'description': self.description,
            'cuda': bool(self.cuda),
            'instruction': self.instruction,
            'output': self.output,
            'accuracy': self.accuracy,
            'type': self.type,
            'likes': self.likes,
            'user_id': self.user_id,
            "creator": self.user.username if self.user else "未知用户",
            'readme': self.readme,
            'created_at': self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

        # 统一处理空值和空字符串
        icon_value = self.icon.strip() if self.icon else None  # 移除空格并转为 None
        base_data['icon'] = ImageURLHandlerUtils.build_full_url(icon_value)

        return base_data

    # @hybrid_property
    # def stars_count(self):
    #     """直接获取该模型的收藏数（适用于单个对象）"""
    #     return self.stars.filter_by(star_type=Star.StarType.MODEL).count()
    #
    # @stars_count.expression
    # def stars_count(cls):
    #     """生成 SQL 表达式（适用于查询排序/过滤）"""
    #     return (
    #         db.select(db.func.count(Star.id))
    #         .where(Star.model_id == cls.id)
    #         .where(Star.star_type == Star.StarType.MODEL)
    #         .correlate(cls)
    #         .scalar_subquery()
    #         .label("stars_count")
    #     )
    #
    # @hybrid_property
    # def sales_count(self):
    #     """访问时触发服务层逻辑"""
    #     from app.order.order_service import OrderService
    #     return OrderService.get_model_sales_count()
    #
    # @sales_count.expression
    # def sales_count(cls):
    #     """生成SQL表达式（用于查询排序/过滤）"""
    #     from app.order.order import Order
    #     return (
    #         db.select(db.func.count(Order.id))
    #         .where(Order.model_id == cls.id)
    #         .where(Order.status == OrderStatus.COMPLETED)
    #         .correlate(cls)
    #         .scalar_subquery()
    #         .label("sales_count")
    #     )

    # def update_star_count(mapper, connection, target):
    #     """收藏变动时自动更新缓存"""
    #     model = target.model
    #     connection.execute(
    #         Model.__table__.update()
    #         .values(star_count=Model.star_count + (1 if target.is_add else -1))
    #         .where(Model.id == model.id)
    #     )
    # # 监听Star表的插入和删除事件
    # event.listen(Star, 'after_insert', update_star_count)
    # event.listen(Star, 'after_delete', update_star_count)
