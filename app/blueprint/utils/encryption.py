from werkzeug.security import generate_password_hash
from app.exts import db
from app.models.user import User
from flask import Flask
from app.config import Config

# 创建 Flask 应用
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

def encrypt_all_passwords():
    with app.app_context():
        # 获取所有用户
        users = User.query.all()
        for user in users:
            # 为每个用户的密码生成加密后的密码
            user.password = generate_password_hash(user.password)
            # 提交更改
        db.session.commit()
        print("All passwords have been updated successfully.")

encrypt_all_passwords()
