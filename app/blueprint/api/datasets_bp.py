import json

from flask import request, Blueprint, jsonify, Response
from flask_restx import Resource, fields, Namespace

from app.blueprint.utils.JSONEncoder import CustomJSONEncoder, create_json_response
from app.exception.errors import DatabaseError
from app.models.dataset import Dataset
from app.services.dataset_service import DatasetService

# 定义排序字段的枚举类型
SORT_BY_CHOICES = ['stars', 'likes', 'downloads', 'size']

# 定义排序顺序的枚举类型（升序或降序）
SORT_ORDER_CHOICES = ['asc', 'desc']

datasets_bp = Blueprint('datasets', __name__)


# 获取数据集列表的函数，
def get_all_datasets():
    # 假设Dataset是SQLAlchemy模型
    datasets = Dataset.query.all()
    if not datasets:
        raise DatabaseError("No datasets found in the database")  # 如果没有数据集，抛出异常
    return [dataset.to_dict() for dataset in datasets]  # 转换为字典形式并返回


# 获取数据集列表的接口
@datasets_bp.route('/list', methods=['GET'])
def list():
    """
    获取所有数据集的信息列表，包括数据集ID、名称、路径、大小等。
    """
    datasets = get_all_datasets()
    return create_json_response(datasets)


@datasets_bp.route('/search', methods=['GET'])
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
    stars = request.args.get('stars', type=int)
    sort_by = request.args.get('sort_by', default='stars')  # 默认排序字段
    sort_order = request.args.get('sort_order', default='asc')  # 默认排序顺序
    page = int(request.args.get('page', 1))  # 默认页码为1
    per_page = int(request.args.get('per_page', 5))  # 默认每页返回5条

    result = DatasetService.search_datasets(
        name=name,
        path=path,
        size_min=size_min,
        size_max=size_max,
        description=description,
        type=type,
        stars=stars,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        per_page=per_page
    )

    # 获取 data 并进行序列化
    data = result['data']

    return create_json_response(data)