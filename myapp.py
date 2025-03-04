import os
from flask import Flask, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.config import config
from app.core.exception import init_error_handlers
from app.core.redis_connection_pool import redis_pool
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

    # 注册蓝图
    register_blueprints(app)

    # 配置Redis连接池
    app.config['REDIS_POOL'] = redis_pool

    return app


def configure_app(app: FlaskApp, env=None):
    """加载并配置应用"""
    # 打印环境变量，检查是否加载成功
    print(f"FLASK_APP: {os.getenv('FLASK_APP')}")
    print(f"FLASK_ENV: {os.getenv('FLASK_ENV')}")

    env = env or os.getenv('FLASK_ENV', 'default')
    if env not in config:
        raise ValueError(f'Invalid environment: {env}')

    # 加载配置
    app.config.from_object(config[env])
    config[env].init_app(app)

    # 配置跨域、转码等
    app.config["JSON_AS_ASCII"] = False
    app.json_encoder = CustomJSONEncoder


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


app = create_app()

if __name__ == '__main__':

    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':

        with app.app_context():  # 显式激活应用上下文
            # 在此处执行需要上下文的代码（如初始化数据）
            print("Registered routes:")
            for rule in app.url_map.iter_rules():
                print(f"{rule.endpoint}: {rule}")
            print("\nSwagger UI available at: http://127.0.0.1:8080/swagger-ui/\n")
            # # 示例：创建订单并更新缓存
            # model_id = 1
            # new_order = Order(model_id=1, order_type=OrderType.MODEL, status=OrderStatus.COMPLETED)
            # db.session.add(new_order)
            # db.session.commit()
            # OrderService.invalidate_sales_cache(model_id=1)

    # 启动应用
    app.run(host='0.0.0.0', port=8080, debug=True)
