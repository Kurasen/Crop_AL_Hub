from flask_limiter import Limiter
from flask_marshmallow.sqla import SQLAlchemyAutoSchema
from marshmallow import Schema, EXCLUDE
from functools import wraps
from webargs.flaskparser import parser
from flask import g, request, current_app


class BaseSchema(Schema):
    class Meta:
        unknown = EXCLUDE  # 禁止未知字段


class AutoSchema(SQLAlchemyAutoSchema):
    """自动生成模型Schema的基类"""

    class Meta(BaseSchema.Meta):
        pass


# 自定义装饰器，动态获取 limiter
def apply_rate_limit(rule):
    # 获取 limiter 实例，避免每次调用时都访问 current_app
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 获取 limiter
            limiter_set = current_app.extensions.get('limiter', set())
            if not limiter_set:
                raise ValueError("Limiter not found in current_app.extensions")
            limiter = next(iter(limiter_set))  # 获取第一个元素

            if not isinstance(limiter, Limiter):
                raise ValueError("limiter is not of type Limiter.")

            # 返回装饰后的函数
            return limiter.limit(rule)(func)(*args, **kwargs)  # 不再调用装饰器
        return wrapper

    return decorator




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
