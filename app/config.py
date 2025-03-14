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
    LIMITER_STORAGE_URI = "redis://redis:6379"
    # 本地
    #LIMITER_STORAGE_URI = "redis://127.0.0.1:6379"
    LIMITER_DEFAULT_LIMITS = ['200 per day', '200 per hour']

    # 算法基础路径
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / "data"

    # 输入输出路径
    INPUT_IMAGES_DIR = DATA_DIR / "images"  # 上传的图片目录
    OUTPUT_DIR = DATA_DIR / "output"  # 算法输出目录

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
        db_host = os.getenv('DB_HOST', 'host.docker.internal')
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
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,  # 默认环境
}
