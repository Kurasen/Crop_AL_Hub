from flask_limiter import Limiter

from marshmallow import EXCLUDE, pre_load, fields, validate
from functools import wraps

from marshmallow.fields import String
from marshmallow_sqlalchemy import SQLAlchemySchema, SQLAlchemyAutoSchema
from webargs.flaskparser import parser
from flask import g, request, current_app

from marshmallow import ValidationError as MarshmallowValidationError


class BaseSchema(SQLAlchemySchema):
    class Meta:
        unknown = EXCLUDE  # 禁止未知字段

        # 自动去除字符串两端空格，空字符串会变成 ""
        string_trim = True

    @pre_load
    def _validate_string_fields(self, data, **kwargs):
        """核心预处理逻辑：拦截空字符串和纯空格"""
        errors = {}

        # 1. 先校验必填字段是否存在
        for field_name, field in self.fields.items():
            if field.required and field_name not in data:
                errors[field_name] = [f"'{field_name}' 字段必须存在"]

        # 2. 再校验所有传入的字符串字段（无论是否必填）
        for field_name, value in data.items():
            field = self.fields.get(field_name)

            if isinstance(field, String):
                # 关键逻辑：如果传了值，则必须是非空内容
                if value.strip() == "":
                    errors.setdefault(field_name, []).append(
                        f"{field_name.capitalize()} 不能为空或空白"
                    )

        if errors:
            raise MarshmallowValidationError(errors)

        return data


class SortBaseSchema(BaseSchema):
    # 排序控制
    sort_by = fields.String(
        validate=validate.OneOf(
            ["stars", "likes"],
            error="排序字段只能是 stars/likes"
        )
    )
    sort_order = fields.String(
        validate=validate.OneOf(
            ["asc", "desc"],
            error="排序顺序只能是 asc/desc")
    )

    # 分页控制
    page = fields.Integer(
        validate=validate.Range(min=1, max=1000),
        metadata={"default": 1, "description": "页码 (1-based)"}
    )
    per_page = fields.Integer(
        validate=validate.Range(min=1, max=100),
        metadata={"default": 5, "description": "每页数量"}
    )


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
                raise ValueError("在current_app.extensions中找不到限制器")
            limiter = next(iter(limiter_set))  # 获取第一个元素

            if not isinstance(limiter, Limiter):
                raise ValueError("限制器不是限制器类型")

            return limiter.limit(
                rule,
                error_message="请求过于频繁，请稍后再试",
                override_defaults=True  # 覆盖默认行为
            )(func)(*args, **kwargs)
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
                raise ValueError("不支持的内容类型")

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
