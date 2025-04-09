import os
import re
from collections import OrderedDict

from flask import g
from marshmallow import fields, validate, validates_schema, validates, pre_load
from marshmallow_sqlalchemy import auto_field
from app.model.model import Model
from app.schemas.base_schema import BaseSchema, SortBaseSchema
from marshmallow import ValidationError as MarshmallowValidationError

from app.utils.image_url_utils import ImageURLHandlerUtils


def validate_characters(value):
    """自定义字符集验证"""
    if not re.fullmatch(r'^[\u4e00-\u9fa5a-zA-Z0-9\s,，;；]+$', value):
        raise MarshmallowValidationError("包含非法字符，只允许中文、英文、数字、空格、中英文逗号和分号")


class ModelBaseSchema(BaseSchema):
    class Meta:
        model = Model
        load_instance = True  # 启用实例化
        include_fk = True  # 包含外键字段

    name = auto_field(
        required=False
    )

    user_id = fields.Int(load_default=lambda: g.current_user.id)  # 自动注入当前用户ID

    input = auto_field(
        allow_none=False,
        required=False
    )

    output = auto_field(
        allow_none=False,
        required=False,
        validate=validate.Regexp(r'.*\.(csv|txt|json)$'),
        error_messages={"required": "Output must be a CSV, TXT, or JSON file"}
    )

    description = auto_field(
        required=False,
        validate=validate.Length(max=50),
        error_messages={"required": "Description must be less than 50 characters"}
    )

    image = auto_field(
        required=False,
        validate=validate.Length(max=50),
        error_messages={"required": "Image should be less than 500 characters"}
    )

    cuda = auto_field(
        required=False,
        validate=validate.OneOf(
            [True, False],
            error="cuda must be true/false"
        )
    )

    instruction = auto_field(
        required=False,
        validate=validate.Length(max=50),
        error_messages={"required": "Instructions should be less than 50 characters"}
    )

    accuracy = auto_field(
        required=False,
        validate=validate.Range(min=0, max=99.99),
        error_messages={"required": "Accuracy should be between 0 and 99.9 characters"}
    )

    type = auto_field(
        required=False
    )

    icon = auto_field(
        required=False
    )

    readme = fields.String(
        required=False,
        validate=[
            fields.validate.Length(max=1000, error="长度需小于1000字符")
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

    @pre_load
    def process_icon(self, data, **kwargs):
        if 'icon' in data:
            print(ImageURLHandlerUtils.validate_photo_file(data['icon']))
            data['icon'] = ImageURLHandlerUtils.validate_photo_file(data['icon'])
        return data


class ModelCreateSchema(ModelBaseSchema):

    name = auto_field(required=True)

    image = auto_field(required=True)


class ModelUpdateSchema(ModelBaseSchema):
    pass


class ModelBaseFieldsMixin:
    name = auto_field(required=False)

    description = auto_field(
        required=False,
        validate=validate.Length(max=50),
        error_messages={"required": "Description must be less than 50 characters"}
    )

    input = auto_field(
        required=False,
        validate=validate.OneOf(
            ["jpg", "jpeg", "png"],
            error="input must be jpg, jpeg, png"
        )
    )

    cuda = auto_field(
        required=False,
        validate=validate.OneOf(
            [True, False],
            error="cuda must be true/false"
        )
    )

    type = auto_field(
        required=False
    )


class ModelSearchSchema(ModelBaseFieldsMixin, SortBaseSchema):
    class Meta:
        model = Model
        ordered = True

    # 排序控制
    sort_by = fields.String(
        validate=validate.OneOf(
            ["likes", "accuracy", "created_at", "updated_at"],
            error="排序字段只能是 likes, accuracy, created_at and updated_at must be less than 100 characters"
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
