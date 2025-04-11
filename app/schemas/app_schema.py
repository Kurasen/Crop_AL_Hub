from flask import g
from marshmallow import fields, validate, pre_load
from marshmallow_sqlalchemy import auto_field

from app.application.app import App
from app.schemas.base_schema import BaseSchema, SortBaseSchema
from app.utils.image_url_utils import ImageURLHandlerUtils


class AppBaseSchema(BaseSchema):
    class Meta:
        model = App
        load_instance = True  # 启用实例化
        include_fk = True  # 包含外键字段

    name = auto_field(
        required=False
    )

    user_id = fields.Int(load_default=lambda: g.current_user.id)  # 自动注入当前用户ID

    icon = auto_field(
        required=False
    )

    description = auto_field(
        required=False,
        validate=validate.Length(max=50),
        error_messages={"required": "Description must be less than 50 characters"}
    )

    url = auto_field(
        required=False,
    )

    @pre_load
    def process_icon(self, data, **kwargs):
        """同时处理 icon 和 url 字段的验证"""
        # 定义需要处理的字段列表
        media_fields = ['icon', 'url']
        for field in media_fields:
            if field in data:
                data[field] = ImageURLHandlerUtils.validate_photo_file(data[field])
        return data


class AppCreateSchema(AppBaseSchema):
    name = auto_field(
        required=True
    )


class AppUpdateSchema(AppBaseSchema):
    pass


class AppBaseFieldsMixin:
    name = auto_field(
        required=False
    )

    icon = auto_field(
        required=False
    )

    description = auto_field(
        required=False,
        validate=validate.Length(max=50),
        error_messages={"required": "Description must be less than 50 characters"}
    )

    url = auto_field(
        required=False,
    )


class AppSearchSchema(AppBaseFieldsMixin, SortBaseSchema):
    class Meta:
        model = App
        ordered = True

    # 排序控制
    sort_by = fields.String(
        validate=validate.OneOf(
            ["likes", "watches", "created_at", "updated_at"],
            error="排序字段只能是 likes, accuracy, created_at and updated_at must be less than 100 characters"
        )
    )
