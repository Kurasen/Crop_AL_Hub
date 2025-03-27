import os

from flask import Flask, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.config import env_config, Config
from app.core.exception import init_error_handlers
from app.core.redis_connection_pool import redis_pool

from app.docker.core.celery_app import CeleryManager

from app.exts import db
from flask_migrate import Migrate
from flask_cors import CORS

from app.utils.json_encoder import CustomJSONEncoder, create_json_response
from flask.app import Flask as FlaskApp


def create_app(env=None):
    """创建Flask应用并配置相关模块"""
    app = Flask(__name__)

    # 获取环境配置
    configure_app(app, env)

    # 注册全局check_json钩子
    configure_global_checks(app)

    # 初始化扩展
    init_extensions(app)

    app.config.update({
        'broker_url': Config.broker_url,
        'worker_concurrency': Config.WORKER_CONCURRENCY,
        'result_backend': Config.result_backend,
        'accept_content': Config.accept_content,
        'task_serializer': Config.task_serializer,
        'result_serializer': Config.result_serializer,
        'timezone': Config.timezone
    })

    from app.docker.core.celery_app import CeleryManager
    CeleryManager.init_celery(app)

    # 配置Redis连接池
    app.config['REDIS_POOL'] = redis_pool

    # 注册蓝图（需在celery后注册）
    register_blueprints(app)

    return app


def configure_app(app: FlaskApp, env=None):
    """加载并配置应用"""
    # 打印环境变量，检查是否加载成功
    print(f"FLASK_APP: {os.getenv('FLASK_APP')}")
    print(f"FLASK_ENV: {os.getenv('FLASK_ENV')}")

    env = env or os.getenv('FLASK_ENV', 'default')
    if env not in env_config:
        raise ValueError(f'Invalid environment: {env}')

    # 加载配置
    app.config.from_object(env_config[env])
    env_config[env].init_app(app)

    app.config['MAX_MEMORY_FILE_SIZE'] = 20 * 1024 * 1024  # 单个文件在内存中的最大大小设置为20MB
    app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 允许200MB请求
    app.config['MAX_MEMORY_BUFFER_SIZE'] = 1024 * 1024  # 1MB内存缓冲区
    app.config['WERKZEUG_MAX_FORM_PARSER_MEMORY'] = 0   # 禁用内存解析限制

    # 配置跨域、转码等
    app.config["JSON_AS_ASCII"] = False
    app.json_encoder = CustomJSONEncoder
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB


def init_extensions(app):
    """初始化Flask扩展"""
    # 初始化Limiter
    Limiter(
        app=app,
        key_func=lambda: get_remote_address(),
        default_limits=app.config["LIMITER_DEFAULT_LIMITS"],
        storage_uri=app.config['LIMITER_STORAGE_URI']
    )

    # 初始化数据库
    db.init_app(app)

    # 初始化Migrate
    Migrate(app, db)

    # 注册错误处理
    init_error_handlers(app)

    # 初始化跨域
    CORS(app, origins='*')

    # 在应用上下文中创建数据库表
    with app.app_context():
        db.create_all()


def register_blueprints(app: FlaskApp):
    """注册应用的所有蓝图"""
    # 延迟导入并注册蓝图
    from app.blueprint.auth_bp import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')

    from app.blueprint.datasets_bp import datasets_bp
    app.register_blueprint(datasets_bp, url_prefix='/api/v1/datasets')

    from app.blueprint.models_bp import models_bp
    app.register_blueprint(models_bp, url_prefix='/api/v1/models')

    from app.blueprint.users_bp import user_bp
    app.register_blueprint(user_bp, url_prefix='/api/v1/users')

    from app.blueprint.stars_bp import stars_bp
    app.register_blueprint(stars_bp, url_prefix='/api/v1/stars')

    from app.blueprint.orders_bp import orders_bp
    app.register_blueprint(orders_bp, url_prefix='/api/v1/orders')


def configure_global_checks(app):
    @app.before_request
    def check_json():
        if request.method == 'OPTIONS':
            return

        # 跳过 logout 路由，避免对没有请求体的请求进行 JSON 解析
        if request.path == '/api/v1/auth/logout':
            return

        allowed_content_types = ['application/json', 'multipart/form-data']

        # 仅检查非 GET/HEAD 请求
        if request.method not in ['GET', 'HEAD']:
            content_type = request.headers.get('Content-Type', '')
            content_length = request.content_length or 0

            # 仅当请求体非空时检查Content-Type, 允许Json或表单上传
            if content_length > 0 and not any(content_type for ct in allowed_content_types):
                if 'application/json' not in content_type:
                    return create_json_response({"error": "Content-Type 必须是 application/json"}, 415)

                # 验证非空请求体的 JSON 有效性
                try:
                    request.get_json()
                except Exception as e:
                    app.logger.error("JSON 解析失败: 错误=%s", str(e))
                    return create_json_response({"error": "请求体必须是有效的 JSON"}, 400)


# 创建 Flask 应用
flask_app = create_app()

celery_app = CeleryManager.get_celery()

if __name__ == '__main__':
    import sys

    # 判断启动模式
    if 'celery' in sys.argv:
        # Celery worker 模式
        celery_app.worker_main(argv=sys.argv[sys.argv.index('celery') + 1:])
    else:
        # 正常启动 Flask
        if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':

            with flask_app.app_context():  # 显式激活应用上下文
                # 在此处执行需要上下文的代码（如初始化数据）
                print("Registered routes:")
                for rule in flask_app.url_map.iter_rules():
                    print(f"{rule.endpoint}: {rule}")

                print("\nSwagger UI available at: http://127.0.0.1:8080/swagger-ui/\n")

                # # 示例：创建订单并更新缓存
                # model_id = 1
                # new_order = Order(model_id=1, order_type=OrderType.MODEL, status=OrderStatus.COMPLETED)
                # db.session.add(new_order)
                # db.session.commit()
                # OrderService.invalidate_sales_cache(model_id=1)

        flask_app.run(host='127.0.0.1', port=5000, debug=True)
