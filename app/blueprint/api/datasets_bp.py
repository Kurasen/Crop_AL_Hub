from flask import request
from flask_restx import Resource, fields, Namespace
from app.exception.errors import DatabaseError
from app.models.dataset import Dataset
from app.services.dataset_service import DatasetService

# 定义排序字段的枚举类型
SORT_BY_CHOICES = ['stars', 'likes']

# 定义排序顺序的枚举类型（升序或降序）
SORT_ORDER_CHOICES = ['asc', 'desc']

datasets_ns = Namespace('datasets', description='Operations related to datasets')

# 定义数据集的模型（返回模型）
dataset_model = datasets_ns.model('Dataset', {
    'id': fields.Integer(required=True, description='Dataset ID'),
    'name': fields.String(required=True, description='Dataset Name'),
    'path': fields.String(required=True, description='Dataset Path'),
    'size': fields.String(required=True, description='Dataset Size in MB/GB'),
    'description': fields.String(description='Dataset Description'),
    'type': fields.String(description='Dataset Type'),  # 新增字段
    'downloads': fields.Integer(description='Number of downloads'),  # 新增字段
    'stars': fields.Integer(description='Dataset star rating'),  # 新增字段
    'likes': fields.Integer(description='Number of likes')  # 新增字段
})


# 获取数据集列表的函数，
def get_datasets_from_db():
    # 假设Dataset是SQLAlchemy模型
    datasets = Dataset.query.all()
    if not datasets:
        raise DatabaseError("No datasets found in the database")  # 如果没有数据集，抛出异常
    return [dataset.to_dict() for dataset in datasets]  # 转换为字典形式并返回


# 获取数据集列表的接口
@datasets_ns.route('/list')
class DatasetsResource(Resource):
    @datasets_ns.doc(description='Retrieve a list of datasets')
    @datasets_ns.marshal_with(dataset_model, as_list=True)  # 标明返回是一个数据集列表
    def get(self):
        """
        获取所有数据集的信息列表，包括数据集ID、名称、路径、大小等。
        """
        datasets = get_datasets_from_db()
        return datasets


@datasets_ns.route('/search')
class DatasetSearchResource(Resource):
    @datasets_ns.doc(description='Search datasets with filters and queries')
    @datasets_ns.param('sort_by', '排序字段，支持的字段包括：stars、size、downloads、name', enum=SORT_BY_CHOICES)
    @datasets_ns.param('sort_order', '排序顺序，选择升序（asc）或降序（desc）', enum=SORT_ORDER_CHOICES)
    @datasets_ns.param('stars', 'Number of stars to search')
    @datasets_ns.param('type', 'Type of the dataset to search, multiple tags separated by comma, semicolon, or space '
                               '(e.g., 玉米,无人机 or 玉米;无人机 or 玉米 无人机)')
    @datasets_ns.param('size_max', 'Maximum size of the dataset (e.g., 1GB)')
    @datasets_ns.param('size_min', 'Minimum size of the dataset (e.g., 100MB)')
    @datasets_ns.param('description', 'Description of the dataset to search')
    @datasets_ns.param('path', 'Path of the dataset to search')
    @datasets_ns.param('name', 'Name of the dataset to search')
    @datasets_ns.marshal_with(dataset_model, as_list=True)
    def get(self):
        """
        查询数据集，支持模糊查询和过滤条件。
        示例请求参数：
        ?name=example&cuda=true&path=/datasets&size_min=100MB&size_max=1GB&type=image&downloads=1000
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

        return result['data'], 200
