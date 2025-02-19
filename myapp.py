
import os

from flask import Flask
from app.blueprint.datasets_bp import datasets_bp
from app.blueprint.models_bp import models_bp
from app.core.redis_connection_pool import RedisConnectionPool
from app.config import config
from app.core.exception import init_error_handlers
from app.exts import db
from app.blueprint.auth_bp import auth_bp
from flask_migrate import Migrate
from flask_cors import CORS
from app.utils.json_encoder import CustomJSONEncoder


def create_app():
    # 打印环境变量，检查是否加载成功
    print(f"FLASK_APP: {os.getenv('FLASK_APP')}")
    print(f"FLASK_ENV: {os.getenv('FLASK_ENV')}")

    # 获取运行环境
    env = os.getenv('FLASK_ENV', 'default')
    app = Flask(__name__)

    # 配置转码
    app.config["JSON_AS_ASCII"] = False

    app.json_encoder = CustomJSONEncoder

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
    Migrate(app, db)

    # 注册全局异常处理
    init_error_handlers(app)

    # 注册蓝图
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(datasets_bp, url_prefix='/datasets')
    app.register_blueprint(models_bp, url_prefix='/models')

    # 从环境变量中获取 Redis 配置
    redis_host = os.getenv('REDIS_HOST', 'localhost')  # 默认使用 localhost
    redis_port = os.getenv('REDIS_PORT', 6379)  # 默认使用端口 6379
    redis_password = os.getenv('REDIS_PASSWORD', None)  # 如果 Redis 启用了密码，填入密码

    # 创建 Redis 连接池管理器实例
    redis_pool = RedisConnectionPool(redis_host, redis_port, redis_password)

    # 将 Redis 连接池管理器存入 app 配置
    app.config['REDIS_POOL'] = redis_pool

    # 检查 Redis 连接是否正常
    with redis_pool.get_redis_connection('default') as redis_client:  # 使用上下文管理器获取连接
        redis_client.ping()  # 执行 ping 操作来检查连接是否正常
        print("Connected to Redis successfully!")


    # # 使用Swagger Editor, 动态加载 swagger.yaml 文件并提供 JSON 接口
    # @app.route('/swagger.json')
    # def swagger_json():
    #     swagger_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'swagger.yaml')
    #     with open(swagger_path, 'r', encoding='utf-8') as file:
    #         yaml_data = yaml.safe_load(file)
    #     return jsonify(yaml_data)
    #
    # # 配置 Swagger UI 路径
    # swagger_url = '/swagger'  # Swagger UI 访问路径
    # api_url = '/swagger.json'  # Swagger 文档的 JSON 文件路径
    #
    # swaggerui_blueprint = get_swaggerui_blueprint(
    #     swagger_url,
    #     api_url,
    #     config={  # Swagger UI 配置
    #         'app_name': "Flask API with Dynamic Swagger"
    #     }
    # )
    #
    # # 注册 Swagger UI 蓝图
    # app.register_blueprint(swaggerui_blueprint, url_prefix=swagger_url)

    # #配置 Flasgger 来自动生成 Swagger 文档(快速迭代)
    # Swagger(app)  # 初始化 Flasgger
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        print("Registered routes:")
        for rule in app.url_map.iter_rules():
            print(f"{rule.endpoint}: {rule}")

    return app


if __name__ == '__main__':

    app = create_app()
    # 只在主进程打印
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        print("Registered routes:")
        for rule in app.url_map.iter_rules():
            print(f"{rule.endpoint}: {rule}")
        print("\nSwagger UI available at: http://127.0.0.1:8080/swagger-ui/\n")
    app.run(debug=True)
