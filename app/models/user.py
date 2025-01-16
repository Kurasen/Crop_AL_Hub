import re
from datetime import datetime
from sqlalchemy.orm import validates
from werkzeug.security import generate_password_hash
from app.exts import db

class UserModel(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True) #个人id
    username = db.Column(db.String(100), unique=True, nullable=False) #用户名
    password = db.Column(db.String(200), nullable=False)  # 增加长度，存储加密后的密码
    email = db.Column(db.String(100), unique=True, nullable=False) #邮箱
    telephone = db.Column(db.String(15), unique=True, nullable=False) #手机号
    landline = db.Column(db.String(8), nullable=False) #座机
    seat = db.Column(db.String(20), nullable=False) #座位
    role = db.Column(db.Integer, nullable=False)  # 职位
    join_time = db.Column(db.DateTime, default=datetime.utcnow)  # 加入时间

    # # 关联管理主体表（假设表名为 management_subjects）
    # management_subject_id = db.Column(db.Integer, ForeignKey('management_subjects.id'), nullable=False)
    # # 关联上级用户表（假设上级也是用户表的一部分）
    # superior_id = db.Column(db.Integer, ForeignKey('user.id'), nullable=True)
    # # 假设 groups 是一对多关系，可以用 ForeignKey 关联一个团队表
    # group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=True)

    management_subject = db.Column(db.String(20), nullable=False) #管理主体
    superior = db.Column(db.String(20), nullable=False) #上级
    group = db.Column(db.String(20), nullable=False)#所属团队


    def __init__(self, username, password, email, telephone, role, management_subject_id, superior_id=None, landline=None, seat=None):
        self.username = username
        self.password = generate_password_hash(password)  # 加密密码
        self.email = email
        self.telephone = telephone
        self.role = role
        self.management_subject_id = management_subject_id
        self.superior_id = superior_id
        self.landline = landline
        self.seat = seat

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