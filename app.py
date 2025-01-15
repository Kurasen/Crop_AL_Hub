
from dotenv import load_dotenv
load_dotenv()  # 自动加载 .env 文件中的环境变量
from flask import Flask, render_template
from config import Config
from exts import db
from blueprint.auth import auth_bp
from flask_migrate import Migrate
from flask_restx import Api


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

    return app

if __name__ == '__main__':
    app = create_app()
    print(app.url_map)  # 打印所有注册的路由
    app.run(debug=True)