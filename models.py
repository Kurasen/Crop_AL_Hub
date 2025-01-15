from datetime import datetime

from werkzeug.security import generate_password_hash, check_password_hash

from exts import db

class UserModel(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  # 增加长度，存储加密后的密码
    email = db.Column(db.String(100), unique=True, nullable=False)
    role = db.Column(db.Integer, nullable=False)  # 更改字段名称，更具描述性
    join_time = db.Column(db.DateTime, default=datetime.utcnow)  # 使用 UTC 时间

    def __init__(self, username, password, email, role):
        self.username = username
        self.password = generate_password_hash(password)  # 加密密码
        self.email = email
        self.role = role

    def check_password(self, password):
        return check_password_hash(self.password, password)  # 验证密码