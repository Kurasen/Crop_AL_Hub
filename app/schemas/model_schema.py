import re
from collections import OrderedDict

from marshmallow import fields, validate, validates_schema, validates, pre_load
from marshmallow_sqlalchemy import auto_field

from app.core.exception import ValidationError
from app.model.model import Model
from app.schemas.base import BaseSchema, SortBaseSchema
from marshmallow import ValidationError as MarshmallowValidationError


def validate_characters(value):
    """自定义字符集验证"""
    if not re.fullmatch(r'^[\u4e00-\u9fa5a-zA-Z0-9\s,，;；]+$', value):
        raise MarshmallowValidationError("包含非法字符，只允许中文、英文、数字、空格、中英文逗号和分号")


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

    type = fields.String(
        required=True,
        validate=[
            fields.validate.Length(max=100, error="长度需小于100字符"),
            validate_characters # 直接引用自定义验证函数
        ]
    )

    @validates('input')
    def validate_input(self, value):
        if value:
            # 如果不为空，检查是否是以 .JPG, .PNG, 或 .JPEG 结尾
            if not re.match(r'.*\.(jpg|png|jpeg)$', value, re.IGNORECASE):
                raise MarshmallowValidationError("Input must be a file with .JPG, .PNG, or .JPEG extension")

    # 在数据加载前处理
    @pre_load
    def preprocess_type_format(self, data, **kwargs):
        """预处理阶段统一格式化 type 字段"""
        if 'type' in data:
            raw_value = data['type']
            # 执行原有的格式化逻辑
            normalized = re.sub(r'[,，;；\s]+', '；', raw_value)
            parts = list(OrderedDict.fromkeys(
                part.strip() for part in normalized.split('；') if part.strip()
            ))
            # 更新到待处理数据中
            data['type'] = '；'.join(parts)
        return data  # 必须返回修改后的数据


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

    type = auto_field(
        validate=validate.Length(
            max=100,
            error="Type must be less than 100 characters"
        )
    )


class ModelSearchSchema(ModelBaseFieldsMixin, SortBaseSchema):
    class Meta:
        model = Model
        ordered = True

    # 排序控制
    sort_by = fields.String(
        validate=validate.OneOf(
            ["likes", "accuracy"],
            error="排序字段只能是 likes/accuracy"
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
