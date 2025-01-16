from dotenv import load_dotenv
from blueprint.models_datasets import models_datasets_bp
from flask import Flask, render_template
from config import Config
from exts import db
from blueprint.auth import auth_bp
from flask_migrate import Migrate

load_dotenv()  # 自动加载 .env 文件中的环境变量


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 初始化数据库
    db.init_app(app)
    migrate = Migrate(app, db)

    # 注册蓝图
    app.register_blueprint(models_datasets_bp, url_prefix='/models_datasets')  # 注册 models_datasets 蓝图
    app.register_blueprint(auth_bp, url_prefix='/auth')

    return app

if __name__ == '__main__':
    app = create_app()
    # print(app.url_map)  # 打印所有注册的路由
    app.run(debug=True)