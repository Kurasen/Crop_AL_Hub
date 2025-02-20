from sqlalchemy import CheckConstraint

from app.exts import db


class User(db.Model):
    __tablename__ = 'user_table'
    __table_args__ = (
        CheckConstraint('email IS NOT NULL OR telephone IS NOT NULL',
                        name='check_email_or_telephone'),
    )
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # 个人id
    username = db.Column(db.String(100), nullable=False)  # 用户昵称
    password = db.Column(db.String(200), nullable=False)  # 密码字段
    email = db.Column(db.String(100), unique=True)  # 邮箱
    telephone = db.Column(db.String(15), unique=True)  # 手机号

    def __init__(self, **kwargs):
        # 确保可为空字段都有默认值
        kwargs.setdefault('email', None)
        kwargs.setdefault('telephone', None)
        super().__init__(**kwargs)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'password': self.password,  # 加密的密码
            'email': self.email,
            'telephone': self.telephone,
        }
