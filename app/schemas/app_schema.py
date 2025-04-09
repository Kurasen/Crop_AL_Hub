from marshmallow import fields, validates, EXCLUDE, validate
from marshmallow_sqlalchemy import auto_field

from app.application.app import App
from app.core.exception import ValidationError
from app.schemas.base_schema import BaseSchema, SortBaseSchema


def validate_file_size(value):
    max_size = 16 * 1024 * 1024  # 16MB
    if value and value.size > max_size:
        raise ValidationError(f"File size should not exceed {max_size / (1024 * 1024)} MB.")
    return value


class AppBaseSchema(BaseSchema):
    class Meta:
        model = App
        load_instance = True  # 启用实例化
        include_fk = True  # 包含外键字段

    name = auto_field(
        required=False
    )

    banner = auto_field(
        required=False
    )

    description = auto_field(
        required=False,
        validate=validate.Length(max=50),
        error_messages={"required": "Description must be less than 50 characters"}
    )

    # 可选：自定义验证逻辑（如 URL 格式检查）
    @validates('banner')
    def validate_url(self, value):
        if not value.startswith(('http://', 'https://')):
            raise ValidationError("URL 必须以 http:// 或 https:// 开头")


class AppCreateSchema(AppBaseSchema):
    name = auto_field(
        required=True
    )

    banner = auto_field(
        required=True
    )


class AppUpdateSchema(AppBaseSchema):
    pass


class AppSearchSchema(AppBaseSchema, SortBaseSchema):
    class Meta:
        model = App
        ordered = True

    # 排序控制
    sort_by = fields.String(
        validate=validate.OneOf(
            ["likes", "accuracy", "created_at", "updated_at"],
            error="排序字段只能是 likes, accuracy, created_at and updated_at must be less than 100 characters"
        )
    )
