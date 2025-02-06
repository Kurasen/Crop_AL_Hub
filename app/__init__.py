import redis
from flask import Flask
from app.blueprint.api.datasets_bp import datasets_ns, dataset_model
from app.blueprint.api.models_bp import models_ns, models_model
from app.blueprint.utils.redis_connection_pool import RedisConnectionPool
from app.config import config
from app.exts import db
from app.blueprint.api.auth_bp import auth_ns, login_model
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
    api.add_namespace(auth_ns, path='/auth')  # 自定义路径
    api.add_namespace(models_ns, path='/models')  # 自定义路径
    api.add_namespace(datasets_ns, path='/datasets')  # 自定义路径

    # 显式注册模型,确保能被全局访问
    api.models['Login'] = login_model
    api.models['Dataset'] = dataset_model
    api.models['ImageUpload'] = models_model

    # 从环境变量中获取 Redis 配置
    redis_host = os.getenv('REDIS_HOST', 'localhost')  # 默认使用 localhost
    redis_port = os.getenv('REDIS_PORT', 6379)        # 默认使用端口 6379
    redis_password = os.getenv('REDIS_PASSWORD', None) # 如果 Redis 启用了密码，填入密码

    # 创建 Redis 连接池管理器实例
    redis_pool = RedisConnectionPool(redis_host, redis_port, redis_password)

    # 将 Redis 连接池管理器存入 app 配置
    app.config['REDIS_POOL'] = redis_pool

    # 检查 Redis 连接是否正常
    try:
        redis_client = redis_pool.get_redis_client('default')  # 获取默认 Redis 客户端
        redis_client.ping()
        print("Connected to Redis successfully!")
    except redis.exceptions.ConnectionError as e:
        print("Failed to connect to Redis:", e)

    # 将 redis_client 绑定到 Flask 应用实例
    #app.redis_client = redis_client

    return app


if __name__ == '__main__':

    app = create_app()

    # 只在主进程打印
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        print("Registered routes:")
        for rule in app.url_map.iter_rules():
            print(f"{rule.endpoint}: {rule}")

    app.run(debug=True)