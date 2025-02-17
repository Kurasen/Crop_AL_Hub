import re

from app.exception.errors import ValidationError


class InputFormatService:

    @staticmethod
    def validate_required_fields(data, fields):
        """检查必填字段是否都存在"""
        missing_fields = [field for field in fields if not data.get(field)]
        if missing_fields:
            raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")

    @staticmethod
    def validate_credentials_format(login_type, login_identifier, password):
        """
        验证登录信息格式，包括邮箱或手机号的格式以及密码格式。
        """
        # 验证手机号或邮箱格式
        InputFormatService.validate_input_format(login_type, login_identifier)

        # 验证密码格式
        InputFormatService.validate_password_format(password)

    # 验证密码格式
    @staticmethod
    def validate_password_format(password):
        # 密码最小长度 8，最大长度 20
        min_length = 6  #测试为6，生产用8
        max_length = 20

        # 密码长度限制
        if len(password) < min_length:
            raise ValidationError(f"Password must be at least {min_length} characters long")
        if len(password) > max_length:
            raise ValidationError(f"Password cannot be more than {max_length} characters long")
        # if not re.search(r'[A-Z]', password):  # 至少一个大写字母
        #     return False, "Password must contain at least one uppercase letter"
        # if not re.search(r'[a-z]', password):  # 至少一个小写字母
        #     return False, "Password must contain at least one lowercase letter"
        # if not re.search(r'[0-9]', password):  # 至少一个数字
        #     return False, "Password must contain at least one number"
        # if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):  # 至少一个特殊字符
        #     return False, "Password must contain at least one special character"

    # 验证输入格式
    @staticmethod
    def validate_input_format(login_type, login_identifier):
        """验证用户名、电话或邮箱格式"""
        patterns = {
            'username': r'^[a-zA-Z0-9_\u4e00-\u9fa5]{3,15}$',
            'telephone': r'^1[3-9]\d{9}$',
            'email': r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        }
        # 获取对应的正则表达式
        pattern = patterns.get(login_type)

        # 如果找不到对应的类型，抛出异常
        if not pattern:
            raise ValidationError(f"Invalid login type '{login_type}' provided.")

        # 使用正则验证
        if not re.match(pattern, login_identifier):
            raise ValidationError(f"Invalid {login_type} format: {login_identifier}.")
