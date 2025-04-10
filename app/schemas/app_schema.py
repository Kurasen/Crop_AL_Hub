from marshmallow import fields, validates, EXCLUDE, validate, pre_load
from marshmallow_sqlalchemy import auto_field

from app.application.app import App
from app.core.exception import ValidationError
from app.schemas.base_schema import BaseSchema, SortBaseSchema
from app.utils.image_url_utils import ImageURLHandlerUtils


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

    icon = auto_field(
        required=False
    )

    description = auto_field(
        required=False,
        validate=validate.Length(max=50),
        error_messages={"required": "Description must be less than 50 characters"}
    )

    @pre_load
    def process_icon(self, data, **kwargs):
        if 'icon' in data:
            print(ImageURLHandlerUtils.validate_photo_file(data['icon']))
            data['icon'] = ImageURLHandlerUtils.validate_photo_file(data['icon'])
        return data


class AppCreateSchema(AppBaseSchema):
    name = auto_field(
        required=True
    )

    icon = auto_field(
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
            ["likes", "watches", "created_at", "updated_at"],
            error="排序字段只能是 likes, accuracy, created_at and updated_at must be less than 100 characters"
        )
    )
