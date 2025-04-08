from marshmallow import fields, validates, EXCLUDE, validate
from marshmallow_sqlalchemy import auto_field

from app.application.app import App
from app.core.exception import ValidationError
from app.schemas.base import BaseSchema, SortBaseSchema
from app.utils.file_process import allowed_file


def validate_file_size(value):
    max_size = 16 * 1024 * 1024  # 16MB
    if value and value.size > max_size:
        raise ValidationError(f"File size should not exceed {max_size / (1024 * 1024)} MB.")
    return value


class AppBaseSchema(BaseSchema):
    name = fields.Str(
        required=False,
        validate=[
            validate.Length(min=1, max=30),
            validate.Regexp(r'^\s*.*?\S+.*\s*$')
        ],
        error_messages={
            "too_short": "Name must be between 1 and 30 characters",
            "too_long": "Name must be between 1 and 30 characters",
            "regexp": "Name cannot be empty or just spaces"
        }
    )
    url = fields.Str(required=False)
    description = auto_field(
        validate=validate.Length(max=500),
        error_messages={"required": "Description must be less than 50 characters"}
    )

    # 可选：自定义验证逻辑（如 URL 格式检查）
    @validates('url')
    def validate_url(self, value):
        if not value.startswith(('http://', 'https://')):
            raise ValidationError("URL 必须以 http:// 或 https:// 开头")

    class Meta:
        model = App
        load_instance = True  # 启用实例化
        include_fk = True  # 包含外键字段
        fields = ("name", "url", "description", "banner")
        strict = True  # 禁止额外字段
        unknown = EXCLUDE


class AppCreateSchema(AppBaseSchema):
    name = fields.Str(
        required=True,
        validate=[
            validate.Length(min=1, max=30),
            validate.Regexp(r'^\s*.*?\S+.*\s*$')
        ],
        error_messages={
            "too_short": "Name must be between 1 and 30 characters",
            "too_long": "Name must be between 1 and 30 characters",
            "regexp": "Name cannot be empty or just spaces"
        }
    )

    url = fields.Str(required=True)


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
