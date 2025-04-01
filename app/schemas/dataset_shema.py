import re
from collections import OrderedDict

from marshmallow import validate, fields, validates_schema, pre_load
from marshmallow_sqlalchemy import auto_field

from marshmallow import ValidationError as MarshmallowValidationError
from app.dataset.dataset import Dataset
from app.dataset.dataset_repo import DatasetRepository
from app.schemas.base import BaseSchema, SortBaseSchema


def validate_size_format(value):
    """验证大小字符串格式 (如 100MB、1.5GB)"""
    if not value:
        return  # 允许空值

    # 正则匹配数字+单位 (支持 K, M, G, T, P, B，大小写不限)
    pattern = r"^(\d+(\.\d+)?)\s*(K|M|G|T|P)?B$"
    match = re.match(pattern, value.strip(), re.IGNORECASE)

    if not match:
        raise MarshmallowValidationError("无效的大小格式，示例: 100MB, 1.5GB")

    # 提取数值和单位
    amount = float(match.group(1))
    unit = match.group(3).upper() if match.group(3) else "B"  # 默认单位是 B

    # 检查数值是否合法
    if amount <= 0:
        raise MarshmallowValidationError("大小必须大于零")


class DatasetBaseSchema(BaseSchema):
    class Meta:
        model = Dataset
        load_instance = True

    name = auto_field(
        required=True,
        validate=[
            validate.Length(min=1, max=100),
            validate.Regexp(r'^\s*.*?\S+.*\s*$')
        ],
        error_messages={
            "required": "Name is required",
            "too_short": "Name must be between 1 and 100 characters",
            "too_long": "Name must be between 1 and 100 characters",
            "regexp": "Name cannot be empty or just spaces"
        }
    )

    path = auto_field(
        validate=validate.Length(
            max=255,
            error="Path must be less than 255 characters"
        )
    )

    size = auto_field(
        validate=validate.Regexp(
            r'^\d+(\.\d+)?(MB|GB|TB)$',
            error="Invalid size format (e.g. 100MB, 1.5GB)"
        )
    )

    description = auto_field(
        validate=validate.Length(
            max=500,
            error="Description must be less than 500 characters"
        )
    )

    type = auto_field(
        validate=validate.Length(
            max=100,
            error="Type must be less than 100 characters"
        )
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


class DatasetCreateSchema(DatasetBaseSchema):
    pass


class DatasetUpdateSchema(DatasetBaseSchema):
    pass


class DatasetBaseFieldsMixin:
    name = auto_field(
        required=False,
        validate=[
            validate.Length(min=1, max=100),
            validate.Regexp(r'^\s*.*?\S+.*\s*$')
        ],
        error_messages={
            "too_short": "Name must be between 1 and 100 characters",
            "too_long": "Name must be between 1 and 100 characters",
            "regexp": "Name cannot be empty or just spaces"
        }
    )

    description = auto_field(
        validate=validate.Length(
            max=500,
            error="Description must be less than 500 characters"
        )
    )

    type = auto_field(
        validate=validate.Length(
            max=100,
            error="Type must be less than 100 characters"
        )
    )


class DatasetSearchSchema(DatasetBaseFieldsMixin, SortBaseSchema):
    class Meta:
        model = Dataset
        ordered = True

    size_min = fields.String(
        validate=validate_size_format,
        metadata={"example": "100MB", "description": "最小大小 (支持单位: B/KB/MB/GB/TB)"}
    )
    size_max = fields.String(
        validate=validate_size_format,
        metadata={"example": "2GB", "description": "最大大小 (支持单位: B/KB/MB/GB/TB)"}
    )

    # 排序控制
    sort_by = fields.String(
        validate=validate.OneOf(
            ["stars", "size", "downloads", "likes", "created_at", "updated_at"],
            error="排序字段只能是 stars/size/downloads/likes/created_at/updated_at"
        )
    )

    @validates_schema
    def validate_size_range(self, data, **kwargs):
        """验证大小范围有效性"""
        if data.get("size_min") and data.get("size_max"):
            min_bytes = DatasetRepository.convert_size_to_bytes(data["size_min"])
            max_bytes = DatasetRepository.convert_size_to_bytes(data["size_max"])
            if min_bytes > max_bytes:
                raise MarshmallowValidationError("size_min 不能大于 size_max")
