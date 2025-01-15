import os

class Config:
    # # 基本配置
    # SECRET_KEY = os.environ.get('SECRET_KEY', 'default_secret_key')  # 从环境变量中读取 SECRET_KEY
    # SQLALCHEMY_TRACK_MODIFICATIONS = False
    #
    # # 数据库配置
    # HOST = os.environ.get('DB_HOST', '127.0.0.1')
    # PORT = os.environ.get('DB_PORT', 3306)
    # DATABASE = os.environ.get('DB_NAME', 'Crop_Al_Hub')
    # USERNAME = os.environ.get('DB_USERNAME', 'root')
    # PASSWORD = os.environ.get('DB_PASSWORD', '123123')
    #
    # DB_URI = 'mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8'.format(
    #     user=USERNAME, password=PASSWORD, host=HOST, port=PORT, database=DATABASE
    # )
    # SQLALCHEMY_DATABASE_URI = DB_URI
    #
    # # 调试模式，取决于环境变量 FLASK_DEBUG
    # DEBUG = os.environ.get('FLASK_DEBUG', True)  # 默认为 True
    SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')  # 默认密钥，避免未设置时报错
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{os.getenv('DB_USERNAME')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() in ['true', '1']
    SQLALCHEMY_TRACK_MODIFICATIONS = False