from flask import request, Blueprint, g

from app import Dataset
from app.dataset.dataset_repo import DatasetRepository
from app.exts import db
from app.schemas.dataset_shema import DatasetSearchSchema, DatasetCreateSchema, DatasetUpdateSchema
from app.token.JWT import admin_required, resource_owner
from app.utils.common.common_service import CommonService
from app.utils.common.json_encoder import create_json_response
from app.dataset.dataset_service import DatasetService

datasets_bp = Blueprint('datasets', __name__, url_prefix='/api/v1/datasets')


@datasets_bp.route('/<int:dataset_id>', methods=['GET'])
def get_model(dataset_id):
    """
    获取特定模型的详细信息
    """
    dataset = DatasetService.get_dataset_by_id(dataset_id)
    return create_json_response({
        "data": dataset.to_dict()
    })


@datasets_bp.route('', methods=['GET'])
def search():
    """
    查询数据集，支持模糊查询和过滤条件。
    示例请求参数：
    ?name=
    """
    search_params = DatasetSearchSchema().load(request.args.to_dict())
    result, status = DatasetService.search_datasets(search_params)
    return create_json_response(result, status)


@datasets_bp.route('/types', methods=['GET'])
def get_all_types():
    """获取所有唯一的模型类型列表"""
    types = CommonService.get_all_types(DatasetRepository)
    return create_json_response({
        "data": {"types": types}
    })


# 创建新数据集
@datasets_bp.route('', methods=['POST'])
@admin_required
def create_dataset():
    """
    创建新数据集
    """
    request_data = request.get_json()
    request_data['user_id'] = g.current_user.id
    dataset_instance = DatasetCreateSchema().load(request_data, session=db.session)
    result, status = DatasetService.create_dataset(dataset_instance)
    return create_json_response(result, status)


# 更新现有数据集
@datasets_bp.route('/<int:dataset_id>', methods=['PUT'])
@resource_owner(model=Dataset, id_param='dataset_id')
def update_dataset(instance):
    """
    更新现有数据集
    """
    updates = request.get_json()
    dataset_instance = DatasetUpdateSchema().load(
        updates,
        instance=instance,  # 传入现有实例
        partial=True,  # 允许部分更新
        session=db.session
    )
    result, status = DatasetService.update_dataset(dataset_instance)
    return create_json_response(result, status)


# 删除现有数据集
@datasets_bp.route('/<int:dataset_id>', methods=['DELETE'])
@resource_owner(model=Dataset, id_param='dataset_id')
def delete_dataset(instance):
    """
    删除现有数据集
    """
    result, status = DatasetService.delete_dataset(instance)
    return create_json_response(result, status)
