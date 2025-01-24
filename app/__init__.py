from flask import Flask
from app.blueprint.api.datasets_bp import datasets_bp, datasets_ns, dataset_model
from app.blueprint.api.models_bp import models_bp, models_ns, models_model
from app.config import config
from app.exts import db
from app.blueprint.api.auth_bp import auth_bp, auth_ns, login_model
from flask_migrate import Migrate
from flask_restx import Api
from flask_cors import CORS
import os



def create_app():

    # 获取运行环境
    env = os.getenv('FLASK_ENV', 'default')
    app = Flask(__name__)

    # 启用 Swagger 编辑器
    app.config['SWAGGER_UI_JSONEDITOR'] = True

    # 配置转码
    app.config["JSON_AS_ASCII"] = False

    # 配置跨域
    CORS(app, cors_allowd_origins='*')

    # 加载配置
    if env in config:
        app.config.from_object(config[env])
        config[env].init_app(app)
    else:
        raise ValueError(f"Invalid environment: {env}")

    # 初始化数据库
    db.init_app(app)
    migrate = Migrate(app, db)
    # 创建 Swagger API 文档

    api = Api(app, version='1.0', title='Flask Login API', description='A simple login API with JWT authentication',
              doc='/swagger-ui')  # 这里设置 Swagger UI 的路径

    # 注册命名空间,
    api.add_namespace(auth_ns)  # 注册 auth 命名空间
    api.add_namespace(datasets_ns)
    api.add_namespace(models_ns)

    # 显式注册模型,确保能被全局访问
    api.models['Login'] = login_model
    api.models['Dataset'] = dataset_model
    api.models['ImageUpload'] = models_model

    # 注册蓝图
    app.register_blueprint(auth_bp)
    app.register_blueprint(datasets_bp)
    app.register_blueprint(models_bp)

    print("Registered routes:")
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint}: {rule}")
    return app


if __name__ == '__main__':

    app = create_app()

    app.run(debug=True)