import os
import sys
from pathlib import Path
from dotenv import load_dotenv

from app.core.exception import logger

# 加载 .env 文件（应用启动时加载）
load_dotenv(Path('.') / '.env')


# 定义基础配置类
class Config:
    """通用配置类"""
    # Flask 配置
    CODE_KEY = os.getenv('CODE_KEY', 'Code_key')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Lock配置
    LOCK_KEY = os.getenv('LOCK_KEY', 'user_login_lock')  # 默认值为 'user_login_lock'
    LOCK_EXPIRE = int(os.getenv('LOCK_EXPIRE', 300))  # 默认过期时间为 300 秒

    # Docker化的limiter 配置（服务器配置）
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

    # 结果生命周期控制
    result_expires = 43200  # 任务结果半天后自动删除（单位：秒）
    task_ignore_result = False  # True=禁用所有结果存储（按需开启）

    # 并发
    worker_concurrency = max(2, os.cpu_count() - 1)  # 留1核给系统
    worker_prefetch_multiplier = 4  # 每个worker预取任务数
    worker_max_tasks_per_child = 100 # 每个子进程执行100个任务后自动重启

    # 可靠性增强
    task_acks_late = True  # 任务完成后才确认
    task_reject_on_worker_lost = True  # Worker异常时重新入队

    # 序列化
    task_serializer = 'json'   # 任务参数使用JSON序列化
    result_serializer = 'json' # 结果使用JSON序列化
    accept_content = ['json'] # 仅接受JSON格式任务
    task_track_started = True # 记录任务开始事件（需配合监控）

    # 时间相关
    timezone = 'Asia/Shanghai'
    """****"""

    # 算法文件存储路径配置
    UPLOAD_FOLDER = Path(r'/home/zhaohonglong/workspace/Crop_Data/input').resolve()  # 使用 Path 对象
    OUTPUT_FOLDER = Path(r'/home/zhaohonglong/workspace/Crop_Data/output').resolve()  # 使用 Path 对象

    USER_FOLDER = Path(r'/home/zhaohonglong/workspace/Crop_Data/user').resolve()

    # Redis配置
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    REDIS_DB = 0

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
    def get_sqlalchemy_test_uri():
        db_username = 'root'
        db_password = '123123'
        db_host = '127.0.0.1'
        db_port = '3306'
        db_name = 'crop_al_hub'

        return f"mysql+pymysql://{db_username}:{db_password}@{db_host}:{db_port}/{db_name}"

    @staticmethod
    def init_app(app):
        pass  # 这里可以放置通用初始化逻辑


class FileConfig:
    # 上传图片存储路径配置
    FILE_BASE_URL = "http://10.0.4.71:8080/file"
    LOCAL_FILE_BASE = "/home/zhaohonglong/workspace/Crop_Data"

    MODEL_ICON_DEFAULT_URL = "http://10.0.4.71:8080/static/icon/model_default_icon.png"

    TEMP_DIR = "/home/zhaohonglong/workspace/Crop_Data/storage/temp"  # 临时存储目录
    TEMP_BASE_URL = "storage/temp"  # 临时文件访问基础路径

    # 上传文件配置
    UPLOAD_CONFIG = {
        "user": {
            "subdirectory": "{user_id}/user/{data_id}/{file_type}",
            "allowed_extensions": ["jpg", "png", "jpeg"],
            "file_types": ["avatars"],
            "max_size": 10 * 1024 * 1024  # 10MB
        },
        "model": {
            "subdirectory": "{user_id}/model/{data_id}/{file_type}",
            "allowed_extensions": ["jpg", "png", "jpeg"],
            "file_types": ["icon", "readme"],  # 固定允许的file_type列表
            "max_size": 100 * 1024 * 1024,  # 100MB
        },
        "dataset": {
            "subdirectory": "{user_id}/dataset/{data_id}/{file_type}",
            "allowed_extensions": ["jpg", "png", "jpeg"],
            "file_types": ["readme"],
            "max_size": 100 * 1024 * 1024  # 500MB
        }
    }


# 开发环境配置
class DevelopmentConfig(Config):
    """开发环境配置"""
    # SQLALCHEMY_DATABASE_URI = Config.get_sqlalchemy_uri()
    if sys.platform == 'linux':
        # Linux系统使用服务器地址
        SQLALCHEMY_DATABASE_URI = Config.get_sqlalchemy_uri()
        logger.info("已连接远程数据库")
    else:
        # Windows/Mac系统自动检测本地Docker
        SQLALCHEMY_DATABASE_URI = Config.get_sqlalchemy_test_uri()
        logger.info("已连接本地测试数据库")

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


# 安全配置类（建议从环境变量加载）
class JWTConfig:
    ACCESS_SECRET_KEY = os.getenv('ACCESS_SECRET_KEY', 'Access_key')
    REFRESH_SECRET_KEY = os.getenv('REFRESH_SECRET_KEY', 'Refresh_key')
    BLACKLIST_REDIS_KEY = os.getenv('BLACKLIST_REDIS_KEY', 'jwt_blacklist')
    ISSUER = "api.testdomain.com"  # 签发者标识
    AUDIENCE = "web.testdomain.com"  # 接收方标识

    # 动态过期时间配置（单位：秒）
    ACCESS_EXPIRE = 36000
    REFRESH_EXPIRE = 604800  # 7天

    # 安全配置
    LAST_PWD_CHANGE_KEY = "user:last_pwd_change:{user_id}"  # 密码最后修改时间键名
