import re

from marshmallow import fields, validate, validates_schema, validates
from marshmallow_sqlalchemy import auto_field

from app.model.model import Model
from app.schemas.base import BaseSchema, SortBaseSchema
from marshmallow import ValidationError as MarshmallowValidationError

class ModelBaseSchema(BaseSchema):
    class Meta:
        model = Model
        load_instance = True
        include_fk = True

    name = fields.Str(
        required=True,
        validate=[
            validate.Length(min=1, max=30),  # 移除 error 参数
            validate.Regexp(r'^\s*.*?\S+.*\s*$')  # 移除 error 参数
        ],
        error_messages={
            "required": "Name is required",
            "too_short": "Name must be between 1 and 30 characters",
            "too_long": "Name must be between 1 and 30 characters",
            "regexp": "Name cannot be empty or just spaces"
        }
    )

    input = auto_field(
        allow_none=True
    )

    output = auto_field(
        allow_none=True,
        validate=validate.Regexp(r'.*\.(csv|txt|json)$'),
        error_messages={"required": "Output must be a CSV, TXT, or JSON file"}
    )

    description = auto_field(
        validate=validate.Length(max=50),
        error_messages={"required": "Description must be less than 50 characters"}
    )

    image = auto_field(
        validate=validate.Length(max=50),
        error_messages={"required": "Image should be less than 500 characters"}
    )

    cuda = auto_field(
        default=False,
        description="是否支持CUDA"
    )

    instruction = auto_field(
        validate=validate.Length(max=50),
        error_messages={"required": "Instructions should be less than 50 characters"}
    )

    accuracy = auto_field(
        validate=validate.Range(min=0, max=99.99),
        error_messages={"required": "Accuracy should be between 0 and 99.9 characters"}
    )

    type = auto_field(
        validate=validate.Length(
            max=100,
            error="Type must be less than 100 characters"
        )
    )

    @validates('input')
    def validate_input(self, value):
        if value:
            # 如果不为空，检查是否是以 .JPG, .PNG, 或 .JPEG 结尾
            if not re.match(r'.*\.(jpg|png|jpeg)$', value, re.IGNORECASE):
                raise MarshmallowValidationError("Input must be a file with .JPG, .PNG, or .JPEG extension")


class ModelCreateSchema(ModelBaseSchema):
    pass


class ModelUpdateSchema(ModelBaseSchema):
    pass


class ModelBaseFieldsMixin:
    name = fields.Str(
        required=False,
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

    description = auto_field(
        validate=validate.Length(max=50),
        error_messages={"required": "Description must be less than 50 characters"}
    )

    input = auto_field(
        validate=validate.OneOf(
            ["jpg", "jpeg", "png"],
            error="input must be jpg, jpeg, png"
        )
    )

    cuda = auto_field(
        validate=validate.OneOf(
            [True, False],
            error="cuda must be true/false"
        )
    )


class ModelSearchSchema(ModelBaseFieldsMixin, SortBaseSchema):
    class Meta:
        model = Model
        ordered = True
    # 排序控制
    sort_by = fields.String(
        validate=validate.OneOf(
            ["stars", "likes", "accuracy", "sales"],
            error="排序字段只能是 stars/likes/like/accuracy"
        )
    )


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
                raise MarshmallowValidationError("Only image files (.jpg, .jpeg, .png) are allowed")
