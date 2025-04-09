import logging
from flask import request
from werkzeug.exceptions import HTTPException, UnsupportedMediaType
from marshmallow import ValidationError as MarshmallowValidationError
from app.utils import create_json_response

# 初始化日志配置，设置错误日志级别
# 配置日志记录
logging.basicConfig(level=logging.INFO,  # 设置日志级别为 INFO
                    format='%(asctime)s - %(levelname)s - %(message)s')  # 设置日志格式

# 获取日志记录器
logger = logging.getLogger(__name__)


# 自定义异常基类
class CustomError(Exception):
    def __init__(self, message="出现了一个错误", status_code=400):
        """
        自定义异常基类，所有自定义异常都继承自此类

        :param message: 错误信息
        :param status_code: 错误对应的HTTP状态码
        """
        self.message = message
        self.status_code = status_code

    def to_dict(self):
        return {
            "error": {
                "code": self.status_code,
                "message": self.message
            }
        }


# 继承自 CustomError 的子类，表示验证失败
class ValidationError(CustomError):
    def __init__(self, message="验证失败", status_code=400):
        """
        参数验证失败的异常

        :param message: 错误信息
        """
        super().__init__(message, status_code)


# 继承自 CustomError 的子类，表示数据库错误
class DatabaseError(CustomError):
    def __init__(self, message="数据库错误", status_code=500):
        """
        数据库错误的异常

        :param message: 错误信息
        """
        super().__init__(message, status_code)


# 继承自 CustomError 的子类，表示认证错误
class AuthenticationError(CustomError):
    def __init__(self, message="认证失败", status_code=401):
        """
        认证失败的异常

        :param message: 错误信息
        """
        super().__init__(message, status_code)


# 继承自 CustomError 的子类，表示认证错误
class TokenError(CustomError):
    def __init__(self, message="Token认证失败", status_code=498):
        """
        认证失败的异常

        :param message: 错误信息
        """
        super().__init__(message, status_code)


class InvalidSizeError(CustomError):
    def __init__(self, size_str, message="大小字符串无效", status_code=422):
        """
        自定义异常，用于处理无效的大小字符串
        """
        self.size_str = size_str
        super().__init__(message, status_code)


class FileUploadError(CustomError):
    def __init__(self, message="文件上传失败", status_code=500):
        """
        文件上传相关的异常
        """
        super().__init__(message, status_code)


class FileValidationError(CustomError):
    def __init__(self, message="文件验证失败", status_code=500):
        """
        文件验证失败
        """
        super().__init__(message, status_code)


class FileSaveError(CustomError):
    def __init__(self, message="图片处理失败", status_code=500):
        """
        文件存储失败
        """
        super().__init__(message, status_code)


class SecurityError(CustomError):
    def __init__(self, message="图片处理失败", status_code=500):
        """
        图像处理相关的异常
        """
        super().__init__(message, status_code)


class ImageProcessingError(CustomError):
    def __init__(self, message="图片处理失败", status_code=500):
        """
        图像处理相关的异常
        """
        super().__init__(message, status_code)


class NotFoundError(CustomError):
    def __init__(self, message="资源未找到", status_code=404):
        """
        资源未找到的异常
        """
        super().__init__(message, status_code)


class RedisConnectionError(CustomError):
    def __init__(self, message="Redis连接失败", status_code=500):
        """
        Redis连接失败的异常
        """
        super().__init__(message, status_code)


class RetryAfterError(CustomError):
    def __init__(self, message="验证码发送请求频繁", status_code=429):
        """
        验证码发送请求频繁的异常
        """
        super().__init__(message, status_code)


class TooManyRequests(CustomError):
    def __init__(self, message="请求过于频繁，请稍后再试", status_code=429):
        """
        超过请求次数限制的异常
        """
        super().__init__(message, status_code)


class ServiceException(CustomError):
    def __init__(self, message="服务异常，请稍后再试", status_code=400):
        """
        服务异常
        """
        super().__init__(message, status_code)


class AlgorithmError(CustomError):
    def __init__(self, message="算法运行失败，请稍后再试", status_code=500):
        """
        算法运行服务异常
        """
        super().__init__(message, status_code)


class PermissionDeniedError(CustomError):
    """权限不足异常"""

    def __init__(self, message="无权操作"):
        super().__init__(message, status_code=403)


class APIError(CustomError):
    """基础API异常"""

    def __init__(self, message="无权操作"):
        super().__init__(message, status_code=403)


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
                request_info = f"Method: {request.method}, URL: {request.url}, Data: No request body"

        except UnsupportedMediaType:
            # 捕获 UnsupportedMediaType 异常，并返回自定义错误信息
            return create_json_response({
                "status": "error",
                "code": 415,
                "message": "不支持的媒体类型"
            }), 415

        # 判断错误类型并构造响应内容
        if isinstance(error, HTTPException):  # Flask 内置的 HTTP 错误
            response = {"error": {"code": error.code, "message": error.description}}
            status_code = error.code
        elif isinstance(error, MarshmallowValidationError):  # 捕获 marshmallow 的 ValidationError
            # marshmallow 异常包含字段错误信息，我们可以提取这些信息
            response = {
                "error": {
                    "message": "参数检验失败",
                    "details": error.messages  # marshmallow 错误信息
                }
            }
            status_code = 400

        elif isinstance(error, CustomError):  # 自定义异常
            response = {"error": {"code": error.status_code, "message": error.message}}
            status_code = error.status_code
        elif isinstance(error, RedisConnectionError):  # 自定义 Redis 异常
            response = {"error": {"code": error.status_code, "message": f"Redis Error: {error.message}"}}
            status_code = error.status_code
        else:  # 其他未知错误
            response = {"status": "error", "code": 500, "message": "内部服务器错误"}
            status_code = 500

        # 记录错误日志，包括错误信息和请求信息
        logger.error(f"Error: {str(error)}, Status Code: {status_code}, Request Info: {request_info}, "
                     f"IP: {request.remote_addr}, User-Agent: {request.user_agent.string}")

        # 返回统一的错误响应
        return create_json_response(response, status_code)
