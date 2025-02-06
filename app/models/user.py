import re

from sqlalchemy.orm import validates
from werkzeug.security import generate_password_hash
from app.exts import db


class User(db.Model):
    __tablename__ = 'user_table'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  #个人id
    username = db.Column(db.String(100), unique=True, nullable=False)  #用户名
    password = db.Column(db.String(200), nullable=False)  # 增加长度，存储加密后的密码
    email = db.Column(db.String(100), unique=True, nullable=False)  #邮箱
    telephone = db.Column(db.String(15), unique=True, nullable=False)  #手机号

    def __init__(self, username, password, email, telephone):
        self.username = username
        self.password = generate_password_hash(password)  # 加密密码
        self.email = email
        self.telephone = telephone

    # 中国手机号格式验证：11位数字，以1开头
    @validates('telephone')
    def validate_telephone(self, key, value):
        pattern = r'^1[3-9]\d{9}$'
        if not re.match(pattern, value):
            raise ValueError("手机号格式无效")
        return value

    # 验证座机号格式
    @validates('landline')
    def validate_landline(self, key, value):
        if value and not value.isdigit():
            raise ValueError("座机号必须为纯数字")
        return value
