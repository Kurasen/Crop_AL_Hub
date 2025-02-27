import re

from app.schemas.base import BaseSchema
from marshmallow import fields, validates, ValidationError, validate, post_load
from marshmallow_sqlalchemy import SQLAlchemySchema

from app.user.user import User


class UserBaseSchema(BaseSchema):
    class Meta:
        model = User
        load_instance = True

    # id = fields.Integer(dump_only=True)  # 只用于响应输出，不用于输入
    username = fields.Str(
        required=False,
        validate=[
            validate.Length(min=1, max=30),  # 移除 error 参数
            validate.Regexp(r'^\s*.*?\S+.*\s*$')  # 移除 error 参数
        ],
        error_messages={
            "too_short": "Name must be between 1 and 30 characters",
            "too_long": "Name must be between 1 and 30 characters",
            "regexp": "Name cannot be empty or just spaces"
        }
    )

    telephone = fields.Str(
        required=False,
        validate=validate.Regexp(r'^1[3-9]\d{9}$'),  # 正则匹配中国手机号
        error_messages={
            'regexp': 'Invalid phone number. Must be a valid Chinese phone number starting with 1 followed by 3-9.'
        }
    )

    email = fields.Email(
        required=False,
        error_messages={
            'invalid': 'Invalid email address format.'
        }
    )


class UserSearchSchema(BaseSchema):
    identity = fields.Str(required=False)

    @post_load
    def identify_search_type(self, data, **kwargs):
        """自动识别输入类型（手机号 > 邮箱 > 用户名）"""
        identity = data['identity']

        # 清空其他字段避免干扰
        data.clear()

        # 识别逻辑
        if re.match(r'^1[3-9]\d{9}$', identity):
            data['search_type'] = 'telephone'
            data['telephone'] = identity
        elif '@' in identity and '.' in identity.split('@')[-1]:
            data['search_type'] = 'email'
            data['email'] = identity
        else:
            data['search_type'] = 'username'
            data['username'] = identity

        return data
