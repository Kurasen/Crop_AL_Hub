from dotenv import load_dotenv
from flask import Flask, render_template
from blueprint.datasets import datasets_bp, datasets_ns
from blueprint.models import models_bp, models_ns
from config import Config
from exts import db
from blueprint.auth import auth_bp, auth_ns, login_model
from flask_migrate import Migrate
from flask_restx import Api
import os
load_dotenv()  # 自动加载 .env 文件中的环境变量

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 初始化数据库
    db.init_app(app)
    migrate = Migrate(app, db)
    # 创建 Swagger API 文档

    api = Api(app, version='1.0', title='Flask Login API', description='A simple login API with JWT authentication',
              doc='/swagger-ui')  # 这里设置 Swagger UI 的路径

    # 注册蓝图
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(datasets_bp, url_prefix='/datasets')  # 注册 datasets蓝图
    app.register_blueprint(models_bp, url_prefix='/models')  # 注册 models 蓝图

    # 注册命名空间,确保 login_model 能被全局访问
    api.add_namespace(auth_ns)  # 注册 auth 命名空间
    api.add_namespace(datasets_ns)
    api.add_namespace(models_ns)

    # 显式注册模型
    api.models['Login'] = login_model

    return app


if __name__ == '__main__':
    app = create_app()
    print(app.url_map)  # 打印所有注册的路由
    app.run(debug=True)
