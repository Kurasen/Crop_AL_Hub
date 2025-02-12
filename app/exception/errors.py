import logging
from flask import jsonify, request
from werkzeug.exceptions import HTTPException, UnsupportedMediaType

# 初始化日志配置，设置错误日志级别
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


# 自定义异常基类
class CustomError(Exception):
    def __init__(self, message="An error occurred", status_code=400):
        """
        自定义异常基类，所有自定义异常都继承自此类

        :param message: 错误信息
        :param status_code: 错误对应的HTTP状态码
        """
        self.message = message
        self.status_code = status_code


# 继承自 CustomError 的子类，表示验证失败
class ValidationError(CustomError):
    def __init__(self, message="Validation failed"):
        """
        参数验证失败的异常

        :param message: 错误信息
        """
        super().__init__(message, 400)


# 继承自 CustomError 的子类，表示数据库错误
class DatabaseError(CustomError):
    def __init__(self, message="Database error"):
        """
        数据库错误的异常

        :param message: 错误信息
        """
        super().__init__(message, 500)


# 继承自 CustomError 的子类，表示认证错误
class AuthenticationError(CustomError):
    def __init__(self, message="Authentication failed"):
        """
        认证失败的异常

        :param message: 错误信息
        """
        super().__init__(message, 401)


# 继承自 CustomError 的子类，表示数据集相关错误
class DatasetError(CustomError):
    def __init__(self, message="Dataset error"):
        """
        数据集错误的异常

        :param message: 错误信息
        """
        super().__init__(message, 400)


class InvalidSizeError(Exception):
    """自定义异常，用于处理无效的大小字符串"""

    def __init__(self, size_str, message="Invalid size string"):
        self.size_str = size_str
        self.message = message
        super().__init__(self.message)


# 全局错误处理函数
def init_error_handlers(app):
    """注册全局错误处理器，用于捕获和处理不同类型的错误"""

    @app.errorhandler(Exception)  # 捕获所有未处理的异常
    def handle_exception(error):
        """
        统一的错误处理函数，捕获所有类型的异常，并做相应的处理

        :param error: 异常对象
        :return: 错误响应，包含错误信息和状态码
        """
        # 获取请求的相关信息，便于日志记录
        try:
            if request.method == 'GET':
                # 对于 GET 请求，记录查询参数，不需要读取请求体
                request_info = f"Method: {request.method}, URL: {request.url}, Data: {request.args.to_dict()}"
            elif request.is_json:
                # 只有在请求是 JSON 格式时，才尝试读取 JSON 数据
                request_info = f"Method: {request.method}, URL: {request.url}, Data: {request.get_json()}"
            else:
                # 如果不是 JSON 格式，记录没有请求体
                request_info = f"Method: {request.method}, URL: {request.url}, Data: No JSON body"
        except UnsupportedMediaType:
            # 捕获 UnsupportedMediaType 异常，并返回自定义错误信息
            return jsonify(
                {"error": {"code": 415, "message": "Unsupported Media Type, please use application/json"}}), 415

        # 判断错误类型并构造响应内容
        if isinstance(error, HTTPException):  # Flask 内置的 HTTP 错误
            response = {"error": {"code": error.code, "message": error.description}}
            status_code = error.code
        elif isinstance(error, CustomError):  # 自定义异常
            response = {"error": {"code": error.status_code, "message": error.message}}
            status_code = error.status_code
        else:  # 其他未知错误
            response = {"error": {"code": 500, "message": "Internal Server Error"}}
            status_code = 500

        # 记录错误日志，包括错误信息和请求信息
        logger.error(f"Error: {error}, Status Code: {status_code}, Request Info: {request_info}")

        # 返回统一的错误响应
        return jsonify(response), status_code