import os

class Config:

    SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')  # 默认密钥，避免未设置时报错
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{os.getenv('DB_USERNAME')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() in ['true', '1']
    SQLALCHEMY_TRACK_MODIFICATIONS = False