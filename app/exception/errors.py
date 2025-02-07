import logging
from flask import jsonify
from werkzeug.exceptions import HTTPException

# 初始化日志
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


class CustomError(Exception):
    """自定义异常基类"""

    def __init__(self, message="An error occurred", status_code=400):
        self.message = message
        self.status_code = status_code


class ValidationError(CustomError):
    """参数校验失败"""

    def __init__(self, message="Validation failed"):
        super().__init__(message, 400)


class DatabaseError(CustomError):
    """数据库错误"""

    def __init__(self, message="Database error"):
        super().__init__(message, 500)


def init_error_handlers(app):
    """全局错误处理"""

    @app.errorhandler(Exception)  # 捕获所有未处理异常
    def handle_exception(error):
        if isinstance(error, HTTPException):  # Flask 内置 HTTP 错误
            response = {"error": {"code": error.code, "message": error.description}}
            status_code = error.code
        elif isinstance(error, CustomError):  # 自定义错误
            response = {"error": {"code": error.status_code, "message": error.message}}
            status_code = error.status_code
        else:  # 其他未知错误
            response = {"error": {"code": 500, "message": "Internal Server Error"}}
            status_code = 500

        logger.error(f"Error: {error}, Status Code: {status_code}")  # 记录日志
        return jsonify(response), status_code
