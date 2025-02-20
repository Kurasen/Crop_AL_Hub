from marshmallow import fields, validate, pre_load

from app.schemas.base import BaseSchema


class DatasetBaseSchema(BaseSchema):
    name = fields.Str(
        required=True,
        validate=[
            validate.Length(min=1, max=30, error="Name must be between 1 and 30 characters"),
            # 确保去除前后空格后仍有非空内容
            validate.Regexp(r'^\s*.*?\S+.*\s*$', error="Name cannot be empty or just spaces")
        ]
    )
    path = fields.Str(validate=validate.Length(max=100, error="Path should be less than 100 characters"))
    description = fields.Str(validate=validate.Length(max=500, error="Description should be less than 500 characters"))
    size = fields.Str(validate=validate.Length(max=10, error="Size should be less than 10 characters"))
    type = fields.Str(validate=validate.Length(max=50, error="Type should be less than 10 characters"))

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
