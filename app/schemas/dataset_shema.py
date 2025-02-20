from marshmallow import fields, validate, pre_load

from app.schemas.base import BaseSchema


class DatasetBaseSchema(BaseSchema):
    name = fields.Str(
        required=True,
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
    path = fields.Str(validate=validate.Length(max=100),
                      error_message="Path must less than 1 and 100 characters")
    description = fields.Str(validate=validate.Length(max=500),
                             error_message="Description must less than 500 characters")
    size = fields.Str(validate=validate.Regexp(r'^\d+(\.\d+)?(MB|GB|TB)$'),
                      error_messages={"required": "Invalid size format"})
    type = fields.Str(validate=validate.Length(max=50),
                      error_messages={"required": "type must less than 50 characters"})

    @pre_load
    def trim_name(self, data, **kwargs):
        """预处理：去除 name 字段的前后空格"""
        if 'name' in data:
            data['name'] = data['name'].strip()
        return data


class DatasetCreateSchema(DatasetBaseSchema):
    pass


class DatasetUpdateSchema(DatasetBaseSchema):
    pass
