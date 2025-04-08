from datetime import datetime

from app.exts import db


class App(db.Model):
    __tablename__ = 'app_table'
    __table_args__ = (
        # 时间约束
        db.CheckConstraint(
            "created_at <= updated_at OR updated_at IS NULL",
            name='time_check'
        ),
    )

    # 定义表的字段
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_table.id'), nullable=False)
    banner = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    likes = db.Column(db.Integer, default=0)
    watches = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<App {self.name}>"

    def __init__(self, **kwargs):
        """
        :param kwargs: 数据集的各个字段参数
        """
        # 使用父类的初始化方法来处理字段初始化
        super().__init__(**kwargs)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "description": self.description,
            "user_id": self.user_id,
            "banner": self.banner,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "likes": self.likes,
            "watches": self.watches
        }
