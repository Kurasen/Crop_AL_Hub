import re

from marshmallow import Schema, fields, validate, validates_schema, ValidationError, pre_load, validates

from app.schemas.base import BaseSchema


class ModelBaseSchema(BaseSchema):
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

    input = fields.Str(
        allow_none=True,
        # validate=validate.OneOf(['image'], error="Input must be 'image'"),
    )
    output = fields.Str(
        allow_none=True,
        validate=validate.Regexp(r'.*\.(csv|txt|json)$'),
        error_messages={"required": "Output must be a CSV, TXT, or JSON file"}
    )
    description = fields.Str(validate=validate.Length(max=50),
                             error_messages={"required": "Description must be longer than 50 characters"})
    image = fields.Str(validate=validate.Length(max=50),
                       error_messages={"required": "Image should be less than 500 characters"})
    cuda = fields.Bool(default=False, description="是否支持CUDA")
    size = fields.Str(validate=validate.Regexp(r'^\d+(\.\d+)?(MB|GB|TB)$'),
                      error_messages={"required": "Invalid size format"})
    instruction = fields.Str(validate=validate.Length(max=50),
                              error_messages={"required": "Instructions should be less than 50 characters"})

    @pre_load
    def trim_name(self, data, **kwargs):
        """预处理：去除 name 字段的前后空格"""
        if 'name' in data:
            data['name'] = data['name'].strip()
        return data

    @validates('input')
    def validate_input(self, value):
        if value:
            # 如果不为空，检查是否是以 .JPG, .PNG, 或 .JPEG 结尾
            if not re.match(r'.*\.(jpg|png|jpeg)$', value, re.IGNORECASE):
                raise ValidationError("Input must be a file with .JPG, .PNG, or .JPEG extension")


class ModelCreateSchema(ModelBaseSchema):
    pass


class ModelUpdateSchema(ModelBaseSchema):
    pass


class ModelRunSchema(BaseSchema):
    """
    用于验证模型运行接口的请求参数
    """
    dataset_id = fields.Int(required=True, error_messages={"required": "Dataset_id is required"})


class ModelTestSchema(BaseSchema):
    """
    用于验证测试模型接口请求中的文件和其他参数
    """
    file = fields.Raw(required=True, error_messages={"required": "未上传文件或未选择文件"})

    @validates_schema
    def validate_file(self, data, **kwargs):
        """
        文件校验，确保上传的是合法文件类型
        """
        file = data.get('file')
        if file:
            if not file.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                raise ValidationError("Only image files (.jpg, .jpeg, .png) are allowed")
