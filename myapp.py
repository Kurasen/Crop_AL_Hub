import os

from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.config import config
from app.core.exception import init_error_handlers
from app.core.redis_connection_pool import redis_pool

from app.exts import db

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

    limiter = Limiter(
        app=app,
        key_func=lambda: get_remote_address(),
        default_limits=['200 per day', '50 per hour'],
    )

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

    # 延迟导入注册蓝图
    from app.blueprint.auth_bp import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.blueprint.datasets_bp import datasets_bp
    app.register_blueprint(datasets_bp, url_prefix='/datasets')

    from app.blueprint.models_bp import models_bp
    app.register_blueprint(models_bp, url_prefix='/models')

    from app.blueprint.user_bp  import user_bp
    app.register_blueprint(user_bp, url_prefix='/user')

    # 将 Redis 连接池管理器存入 app 配置
    app.config['REDIS_POOL'] = redis_pool

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
