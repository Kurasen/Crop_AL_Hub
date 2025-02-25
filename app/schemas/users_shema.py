from app.schemas.base import BaseSchema
from marshmallow import fields, validates, ValidationError
from marshmallow_sqlalchemy import SQLAlchemySchema

from app.user.user import User


class UserBaseSchema(BaseSchema):

    id = fields.Integer(dump_only=True)  # 只用于响应输出，不用于输入
    username = fields.String(required=True, error_messages={"required": "用户名不能为空"})
    password = fields.String(required=True, error_messages={"required": "密码不能为空"})
    email = fields.Email()  # 自动验证邮箱格式
    telephone = fields.String()
