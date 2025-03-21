import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件（应用启动时加载）
load_dotenv(Path('.') / '.env')


# 定义基础配置类
class Config:
    """通用配置类"""
    # Flask 配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Lock配置
    LOCK_KEY = os.getenv('LOCK_KEY', 'user_login_lock')  # 默认值为 'user_login_lock'
    LOCK_EXPIRE = int(os.getenv('LOCK_EXPIRE', 300))  # 默认过期时间为 300 秒

    # Docker化的limiter 配置
    #LIMITER_STORAGE_URI = "redis://redis:6379"
    # 本地
    LIMITER_STORAGE_URI = "redis://127.0.0.1:6379"

    LIMITER_DEFAULT_LIMITS = ['1000000 per day', '1000000 per hour']
    # # 根据环境变量决定是否启用限制
    # if os.getenv("FLASK_ENV") == "development":
    #     LIMITER_DEFAULT_LIMITS = []  # 开发环境禁用限流
    # else:
    #     LIMITER_DEFAULT_LIMITS = ['200 per day', '200 per hour']  # 生产环境启用限流

    """Celery统一配置类"""
    broker_url = 'redis://localhost:6379/0'
    result_backend = 'redis://localhost:6379/0'
    task_serializer = 'json'
    result_serializer = 'json'
    accept_content = ['json']
    WORKER_CONCURRENCY = os.cpu_count() * 2  # 根据CPU核心数优化
    task_track_started = True
    timezone = 'Asia/Shanghai'


# 算法文件存储路径配置
    UPLOAD_FOLDER = Path(r'/home/zhaohonglong/workspace/Crop_AL_Hub-API/app/data/input').resolve()  # 使用 Path 对象
    OUTPUT_FOLDER = Path(r'/home/zhaohonglong/workspace/Crop_AL_Hub-API/app/data/output').resolve()  # 使用 Path 对象

    # Redis配置
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    REDIS_DB = 0

    # Docker配置
    DOCKER_IMAGE_PREFIX = "my-algorithm-"  # 算法镜像名前缀（例如：my-algorithm-face-detection）

    # 数据库配置
    @staticmethod
    def get_sqlalchemy_uri():
        db_username = os.getenv('DB_USERNAME', 'root')
        db_password = os.getenv('DB_PASSWORD', '123123')
        db_host = os.getenv('DB_HOST', '10.0.4.71')
        db_port = os.getenv('DB_PORT', '3306')
        db_name = os.getenv('DB_NAME', 'crop_al_hub')

        return f"mysql+pymysql://{db_username}:{db_password}@{db_host}:{db_port}/{db_name}"

    @staticmethod
    def init_app(app):
        pass  # 这里可以放置通用初始化逻辑


# 开发环境配置
class DevelopmentConfig(Config):
    """开发环境配置"""
    SQLALCHEMY_DATABASE_URI = Config.get_sqlalchemy_uri()

    @staticmethod
    def init_app(app):
        """开发环境的初始化逻辑"""
        # 加载 .env 文件
        load_dotenv(Path('.') / '.env')


# 生产环境配置
class ProductionConfig(Config):
    """生产环境配置"""
    SQLALCHEMY_DATABASE_URI = Config.get_sqlalchemy_uri()


# 配置映射
env_config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,  # 默认环境
}
