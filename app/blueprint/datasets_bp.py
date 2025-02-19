from flask import request, Blueprint
from app.utils.json_encoder import create_json_response
from app.dataset.dataset_service import DatasetService

datasets_bp = Blueprint('datasets', __name__)


@datasets_bp.route('', methods=['GET'])
def search():
    """
    查询数据集，支持模糊查询和过滤条件。
    示例请求参数：
    ?name=
    """
    name = request.args.get('name')
    path = request.args.get('path')
    size_min = request.args.get('size_min')
    size_max = request.args.get('size_max')
    description = request.args.get('description')
    type = request.args.get('type')
    sort_by = request.args.get('sort_by')  # 默认排序字段
    sort_order = request.args.get('sort_order')  # 默认排序顺序
    page = int(request.args.get('page', 1))  # 默认页码为1
    per_page = int(request.args.get('per_page', 5))  # 默认每页返回5条

    result = DatasetService.search_datasets(
        name=name,
        path=path,
        size_min=size_min,
        size_max=size_max,
        description=description,
        type=type,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        per_page=per_page
    )

    return create_json_response(result)


# 创建新数据集
@datasets_bp.route('', methods=['POST'])
def create_dataset():
    """
    创建新数据集
    """
    data = request.get_json()

    dataset_data, status = DatasetService.create_dataset(data)
    return create_json_response(dataset_data, status)


# 更新现有数据集
@datasets_bp.route('/<int:dataset_id>', methods=['PUT'])
def update_dataset(dataset_id):
    """
    更新现有数据集
    """
    data = request.get_json()

    updated_dataset, status = DatasetService.update_dataset(dataset_id, data)
    return create_json_response(updated_dataset, status)


# 删除现有数据集
@datasets_bp.route('/<int:dataset_id>', methods=['DELETE'])
def delete_dataset(dataset_id):
    """
    删除现有数据集
    """
    response, status = DatasetService.delete_dataset(dataset_id)
    return create_json_response(response, status)
