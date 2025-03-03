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

    LOCK_KEY = os.getenv('LOCK_KEY', 'user_login_lock')  # 默认值为 'user_login_lock'
    LOCK_EXPIRE = int(os.getenv('LOCK_EXPIRE', 300))  # 默认过期时间为 300 秒

    LIMITER_STORAGE_URI = "redis://redis:6379"
    LIMITER_DEFAULT_LIMITS = ['200 per day', '50 per hour']

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
