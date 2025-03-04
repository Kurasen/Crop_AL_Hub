from marshmallow import fields, validate, validates_schema

from app.core.exception import ValidationError
from app.dataset.dataset_service import DatasetService
from app.model.model_service import ModelService
from app.schemas.base import BaseSchema
from app.star.star import StarType


class StarCreateSchema(BaseSchema):
    target_id = fields.Int(required=True)
    star_type = fields.Str(
        required=True,
        validate=validate.OneOf([t.value for t in StarType])
    )
    user_id = fields.Int(required=True)

    @validates_schema
    def validate_target_consistency(self, data, **kwargs):
        star_type = data.get('star_type')
        target_id = data.get('target_id')

        # 此处可调用 Service 层检查目标是否存在（例如 ModelService.model_exists）
        # 示例伪代码：
        if star_type != StarType.MODEL.value and star_type != StarType.DATASET.value:
            raise ValidationError('Star type must be model or dataset')
        if star_type == StarType.MODEL.value:
            ModelService.get_model_by_id(target_id)
        elif star_type == StarType.DATASET.value:
            DatasetService.get_dataset_by_id(target_id)
