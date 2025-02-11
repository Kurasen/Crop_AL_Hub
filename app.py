import redis
import yaml

from flask import Flask, jsonify
from flask_swagger_ui import get_swaggerui_blueprint

from app.core.redis_connection_pool import RedisConnectionPool
from app.config import config
from app.exception.errors import init_error_handlers
from app.exts import db
from app.blueprint.api.auth_bp import auth_bp
from flask_migrate import Migrate
from flask_cors import CORS
import os


def create_app():
    # 获取运行环境
    env = os.getenv('FLASK_ENV', 'default')
    app = Flask(__name__)

    # 配置转码
    app.config["JSON_AS_ASCII"] = False

    # 配置跨域
    CORS(app, origins='*')

    # 加载配置
    if env in config:
        app.config.from_object(config[env])
        config[env].init_app(app)
    else:
        raise ValueError(f"Invalid environment: {env}")

    # 初始化数据库
    db.init_app(app)
    migrate = Migrate(app, db)

    # 注册全局异常处理
    init_error_handlers(app)

    # 注册蓝图
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # 从环境变量中获取 Redis 配置
    redis_host = os.getenv('REDIS_HOST', 'localhost')  # 默认使用 localhost
    redis_port = os.getenv('REDIS_PORT', 6379)  # 默认使用端口 6379
    redis_password = os.getenv('REDIS_PASSWORD', None)  # 如果 Redis 启用了密码，填入密码

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
        app.logger.error(f"Failed to connect to Redis: {str(e)}")

    # 动态加载 swagger.yaml 文件并提供 JSON 接口
    @app.route('/swagger.json')
    def swagger_json():
        swagger_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'swagger.yaml')
        with open(swagger_path, 'r', encoding='utf-8') as file:
            yaml_data = yaml.safe_load(file)
        return jsonify(yaml_data)

    # 配置 Swagger UI 路径
    swagger_url = '/swagger'  # Swagger UI 访问路径
    api_url = '/swagger.json'  # Swagger 文档的 JSON 文件路径

    swaggerui_blueprint = get_swaggerui_blueprint(
        swagger_url,
        api_url,
        config={  # Swagger UI 配置
            'app_name': "Flask API with Dynamic Swagger"
        }
    )

    # 注册 Swagger UI 蓝图
    app.register_blueprint(swaggerui_blueprint, url_prefix=swagger_url)

    return app


if __name__ == '__main__':

    app = create_app()
    # 只在主进程打印
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        print("Registered routes:")
        for rule in app.url_map.iter_rules():
            print(f"{rule.endpoint}: {rule}")
        print("\nSwagger UI available at: http://127.0.0.1:5000/swagger\n")
    app.run(debug=True)
