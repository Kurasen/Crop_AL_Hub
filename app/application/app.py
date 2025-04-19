from datetime import datetime

from app.config import FileConfig
from app.exts import db
from app.utils.image_url_utils import ImageURLHandlerUtils


class App(db.Model):
    __tablename__ = 'app_table'
    __table_args__ = (
        db.Index('idx_created_at', 'created_at'),
        db.Index('idx_updated_at', 'updated_at'),
        db.Index('idx_likes', 'likes'),
        db.Index('idx_watches', 'watches'),
        # 时间约束
        db.CheckConstraint(
            "created_at <= updated_at OR updated_at IS NULL",
            name='time_check'
        ),
    )
    # 定义表的字段
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_table.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    likes = db.Column(db.Integer, default=0)
    watches = db.Column(db.Integer, default=0)
    icon = db.Column(db.String(255), nullable=True, default=None)

    user = db.relationship("User", back_populates="apps")

    tasks = db.relationship("Task", back_populates="app")

    def __repr__(self):
        return f"<App {self.name}>"

    def __init__(self, **kwargs):
        """
        :param kwargs: 数据集的各个字段参数
        """
        # 使用父类的初始化方法来处理字段初始化
        super().__init__(**kwargs)

    def to_dict(self):
        base_data = {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "description": self.description,
            "user_id": self.user_id,
            "creator":  self.user.username if self.user else "未知用户",
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "likes": self.likes,
            "watches": self.watches
        }
        # 统一处理空值和空字符串
        icon_value = self.icon.strip() if self.icon else None  # 移除空格并转为 None

        # 新增逻辑：当 icon 为空时，直接指向静态资源默认图标
        if not icon_value:
            # 硬编码静态资源路径（绕过 FILE_BASE_URL）
            base_data['icon'] = FileConfig.APP_ICON_DEFAULT_URL
        else:
            # 非空时走原有逻辑（如上传文件路径拼接）
            base_data['icon'] = ImageURLHandlerUtils.build_full_url(icon_value)


        return base_data
