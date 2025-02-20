from flask_marshmallow.sqla import SQLAlchemyAutoSchema
from marshmallow import Schema, EXCLUDE, validate, fields
from functools import wraps
from webargs.flaskparser import parser
from flask import g, request


class BaseSchema(Schema):
    class Meta:
        unknown = EXCLUDE  # 禁止未知字段


class AutoSchema(SQLAlchemyAutoSchema):
    """自动生成模型Schema的基类"""

    class Meta(BaseSchema.Meta):
        pass


def validate_request(schema_cls, content_type="json"):
    """通用请求验证装饰器

    :param schema_cls: 继承自marshmallow.Schema的验证类
    :param content_type: 允许的内容类型（json/form）
    """

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # 根据内容类型选择解析位置
            locations = ()
            if content_type == "json":
                locations = ("json",)
            elif content_type == "form":
                locations = ("form",)
            else:
                raise ValueError("Unsupported content type")

            # 执行webargs解析验证
            parsed_data = parser.parse(
                schema_cls(),
                req=request,
                locations=locations
            )

            # 将验证后的数据存入g对象
            g.validated_data = parsed_data
            return f(*args, **kwargs)

        return wrapper

    return decorator
