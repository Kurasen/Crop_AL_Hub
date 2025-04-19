import os
import re
from collections import OrderedDict

from flask import g
from marshmallow import fields, validate, validates_schema, validates, pre_load
from marshmallow_sqlalchemy import auto_field

from app.config import FileConfig
from app.model.model import Model
from app.schemas.base_schema import BaseSchema, SortBaseSchema
from marshmallow import ValidationError as MarshmallowValidationError

from app.schemas.users_shema import UserBaseSchema
from app.utils.image_url_utils import ImageURLHandlerUtils


def validate_characters(value):
    """自定义字符集验证"""
    if not re.fullmatch(r'^[\u4e00-\u9fa5a-zA-Z0-9\s,，;；]+$', value):
        raise MarshmallowValidationError("包含非法字符，只允许中文、英文、数字、空格、中英文逗号和分号")


class ModelInputBaseSchema(BaseSchema):
    class Meta(BaseSchema.Meta):  # 显式继承基类配置
        model = Model
        load_instance = True
        include_fk = True

    name = auto_field(
        required=False,
        validate=[
            validate.Length(min=1, max=50),
            validate.Regexp(r'^[\w\u4e00-\u9fa5]+$', error="只能包含中文、英文、数字和下划线")
        ]
    )

    user_id = fields.Int(
        load_only=True,  # 只用于输入，不输出
        load_default=lambda: g.current_user.id
    )

    input = auto_field(
        required=False,  # 允许客户端不传此字段
        allow_none=False,  # 但如果传了值，则不能为 null
        validate=[
            validate.Regexp(r'.*\.(jpg|png|jpeg|JPG|PNG|JPEG)$', error="必须为 JPG/PNG/JPEG 文件")
        ]
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

    readme = auto_field(
        required=False,
        validate=[
            fields.validate.Length(max=1000, error="长度需小于1000字符")
        ]
    )

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
            excluded_urls = [
                FileConfig.MODEL_ICON_DEFAULT_URL,
                FileConfig.APP_ICON_DEFAULT_URL
            ]
            if data['icon'] not in excluded_urls:
                data['icon'] = ImageURLHandlerUtils.validate_photo_file(data['icon'])
            else:
                data['icon'] = None
        return data


class ModelCreateSchema(ModelInputBaseSchema):
    """专门用于创建模型的校验"""

    class Meta(ModelInputBaseSchema.Meta):
        pass  # 继承父类配置

    name = auto_field(required=True)  # 覆盖父类定义


class ModelUpdateSchema(ModelInputBaseSchema):
    class Meta(ModelInputBaseSchema.Meta):
        pass


class ModelResponseSchema(BaseSchema):
    """专门用于响应数据序列化"""

    class Meta(ModelInputBaseSchema.Meta):
        fields = (
            "id", "name", "description", "image",
            "input", "cuda", "instruction", "output",
            "accuracy", "created_at", "user_info", "readme"
        )
        dump_only = ("id", "created_at", "user_info")

        # 可以添加响应专用格式处理
    user_info = fields.Nested(UserBaseSchema, attribute='user')  # 嵌套其他 Schema


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
