from flask import request, Blueprint

from app.utils.json_encoder import create_json_response
from app.dataset.dataset_service import DatasetService

datasets_bp = Blueprint('datasets', __name__, url_prefix='/api/v1/datasets')


@datasets_bp.route('/<int:dataset_id>', methods=['GET'])
def get_model(dataset_id):
    """
    获取特定模型的详细信息
    """
    dataset = DatasetService.get_dataset_by_id(dataset_id)
    return create_json_response(dataset.to_dict())


@datasets_bp.route('', methods=['GET'])
def search():
    """
    查询数据集，支持模糊查询和过滤条件。
    示例请求参数：
    ?name=
    """
    result = DatasetService.search_datasets(request.args.to_dict())

    return create_json_response(result)


# 创建新数据集
@datasets_bp.route('', methods=['POST'])
def create_dataset():
    """
    创建新数据集
    """
    result, status = DatasetService.create_dataset(request.get_json())
    return create_json_response(result, status)


# 更新现有数据集
@datasets_bp.route('/<int:dataset_id>', methods=['PUT'])
def update_dataset(dataset_id):
    """
    更新现有数据集
    """
    result, status = DatasetService.update_dataset(dataset_id, request.get_json())
    return create_json_response(result, status)


# 删除现有数据集
@datasets_bp.route('/<int:dataset_id>', methods=['DELETE'])
def delete_dataset(dataset_id):
    """
    删除现有数据集
    """
    result, status = DatasetService.delete_dataset(dataset_id)
    return create_json_response(result, status)
