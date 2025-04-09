import re

from marshmallow import fields, validate, validates_schema

from app.core.exception import ValidationError
from app.schemas.base_schema import BaseSchema
from marshmallow import ValidationError as MarshmallowValidationError


# 基础登录验证逻辑
class AuthBaseSchema(BaseSchema):
    login_type = fields.Str(
        required=True,
        validate=validate.OneOf(['telephone', 'email'], error="登陆类型必须使用手机号或邮箱登录")
    )
    login_identifier = fields.Str(required=True)

    @validates_schema
    def validate_identifier_format(self, data, **kwargs):
        """根据 login_type 动态验证标识符格式"""
        login_type = data.get('login_type')
        identifier = data.get('login_identifier')

        if login_type == 'telephone':
            if not re.match(r'^1[3-9]\d{9}$', identifier):
                raise MarshmallowValidationError("电话号码格式错误")
        elif login_type == 'email':
            try:
                validate.Email()(identifier)
            except ValidationError:
                raise MarshmallowValidationError("邮箱格式错误")


class AuthWithPasswordSchema(AuthBaseSchema):
    password = fields.Str(required=True, load_only=True)

    @validates_schema
    def validate_password_length(self, data, **kwargs):
        """密码格式校验"""
        password = data.get('password')
        min_length = 6  #测试为6，生产用8
        max_length = 20
        if len(password) < min_length:
            raise MarshmallowValidationError(f"密码长度必须至少为｛min_length｝个字符")
        if len(password) > max_length:
            raise MarshmallowValidationError(f"密码长度必须至多为｛min_length｝个字符")
        # if not re.search(r'[A-Z]', password):  # 至少一个大写字母
        #     return False, "Password must contain at least one uppercase letter"
        # if not re.search(r'[a-z]', password):  # 至少一个小写字母
        #     return False, "Password must contain at least one lowercase letter"
        # if not re.search(r'[0-9]', password):  # 至少一个数字
        #     return False, "Password must contain at least one number"
        # if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):  # 至少一个特殊字符
        #     return False, "Password must contain at least one special character"


class UserCreateSchema(AuthWithPasswordSchema):
    code = fields.Int(required=True, validate=validate.Range(min=100000, max=999999, error="验证码格式错误"))
    username = fields.Str(required=True, validate=validate.Length(min=3, error="用户名格式错误"))

    @validates_schema
    def validate_credentials(self, data, **kwargs):
        pass


class UserLoginSchema(AuthWithPasswordSchema):
    pass


class GenerateCodeSchema(AuthBaseSchema):
    pass
