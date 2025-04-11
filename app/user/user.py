from sqlalchemy import CheckConstraint, Enum

from app.exts import db


class User(db.Model):
    __tablename__ = 'user_table'
    __table_args__ = (
        # 确保邮箱或手机号至少有一个存在
        CheckConstraint('email IS NOT NULL OR telephone IS NOT NULL',
                        name='check_email_or_telephone'),
        # identity 必须是四个预设值之一
        CheckConstraint("identity IN ('研究员', '学生', '群众', '其他')",
                        name='check_identity_values')
    )
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # 个人id
    username = db.Column(db.String(100), nullable=False, index=True)  # 用户昵称
    password = db.Column(db.String(200), nullable=False)  # 密码字段
    email = db.Column(db.String(100), unique=True)  # 邮箱
    telephone = db.Column(db.String(15), unique=True)  # 手机号
    role_id = db.Column(db.Integer, default=1)  # 用户角色
    identity = db.Column(
        Enum('研究员', '学生', '群众', '其他', name='identity_types'),
        nullable=False,  # 根据需求决定是否允许为空
        default='群众'  # 可选：设置默认值
    )
    workspace = db.Column(db.String(50), nullable=True)

    # 定义正向关系(一对多)
    apps = db.relationship("App", back_populates="user")  # back_populates 指向 App.user
    models = db.relationship("Model", back_populates="user")
    datasets = db.relationship("Dataset", back_populates="user")
    tasks = db.relationship("Task", back_populates="user")

    # stars = db.relationship("Star", back_populates="user", lazy="dynamic")
    # orders = db.relationship("Order", back_populates="user", lazy="dynamic")

    def __init__(self, **kwargs):
        # 确保可为空字段都有默认值
        kwargs.setdefault('email', None)
        kwargs.setdefault('telephone', None)
        super().__init__(**kwargs)

    @property
    def role(self) -> str:
        """ 通过属性访问角色名称 """
        return 'admin' if self.role_id == 0 else 'user'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            #'password': self.password,  # 加密的密码
            'email': self.mask_email(self.email) if self.email else None,
            'telephone': self.mask_telephone(self.telephone) if self.telephone else None,
            'role': self.role,
            'identity': self.identity,
            'workspace': self.workspace,
        }

    @staticmethod
    def mask_email(email):
        parts = email.split('@')
        if len(parts) != 2:
            return email
        name = parts[0]
        if len(name) <= 1:
            return f"*@{parts[1]}"
        return f"{name[0]}***@{parts[1]}"

    @staticmethod
    def mask_telephone(telephone):
        if len(telephone) != 11:
            return telephone
        return telephone[:3] + "****" + telephone[-4:]
