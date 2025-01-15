from werkzeug.security import generate_password_hash
from exts import db
from models import UserModel
from flask import Flask
from config import Config

# 创建 Flask 应用
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

def encrypt_existing_password():
    with app.app_context():  # 激活应用程序上下文
        user = UserModel.query.filter_by(username='test001').first()
        if user:
            user.password = generate_password_hash('123123')  # 加密明文密码
            db.session.commit()
            print("Password updated successfully.")
        else:
            print("User not found.")

encrypt_existing_password()
