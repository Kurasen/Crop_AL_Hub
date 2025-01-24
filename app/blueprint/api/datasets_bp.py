from flask import Blueprint, jsonify, request
from flask_restx import Api, Resource, fields

from app.models.dataset import Dataset
from app.repositories.dataset_repo import DatasetRepository

# 创建蓝图
datasets_bp = Blueprint('datasets', __name__)

# 创建 API 对象
api = Api(datasets_bp, version='1.0', title='Flask Datasets API', description='Retrieve datasets')

# 定义命名空间：数据集
datasets_ns = api.namespace('datasets', description='Operations related to datasets')

# 定义数据集的模型（返回模型）
dataset_model = api.model('Dataset', {
    'id': fields.Integer(required=True, description='Dataset ID'),
    'name': fields.String(required=True, description='Dataset Name'),
    'path': fields.String(required=True, description='Dataset Path'),
    'size': fields.String(required=True, description='Dataset Size in MB/GB'),
    'describe': fields.String(description='Dataset Description'),
    'cuda': fields.Boolean(required=True, description='Is CUDA supported')
})

# 注册模型
api.models['Dataset'] = dataset_model  # 注册模型


# 获取数据集列表的函数，
def get_datasets_from_db():
    # 从数据库中查询所有数据集
    datasets = Dataset.query.all()  # 假设Dataset是SQLAlchemy模型
    return [dataset.to_dict() for dataset in datasets]  # 转换为字典形式并返回


# 获取数据集列表的接口
@datasets_ns.route('/list')
class DatasetsResource(Resource):
    @api.doc(description='Retrieve a list of datasets')
    @api.marshal_with(dataset_model, as_list=True)  # 标明返回是一个数据集列表
    def get(self):
        return get_datasets_from_db()


@datasets_ns.route('/search')
class DatasetSearchResource(Resource):
    @api.doc(description='Search datasets with filters and queries')
    @api.param('name', 'Name of the dataset to search')
    @api.param('path', 'Path of the dataset to search')
    @api.param('cuda', 'CUDA support (True or False)')
    @api.param('size_min', 'Minimum size of the dataset (e.g., 100MB)')
    @api.param('size_max', 'Maximum size of the dataset (e.g., 1GB)')
    @api.marshal_with(dataset_model, as_list=True)
    def get(self):

        """
        查询数据集，支持模糊查询和过滤条件。
        示例请求参数：
        ?name=example&cuda=true&path=/datasets&size_min=100MB&size_max=1GB
        """
        name = request.args.get('name')
        path = request.args.get('path')
        cuda = request.args.get('cuda', type=lambda v: v.lower() == 'true')
        size_min = request.args.get('size_min')
        size_max = request.args.get('size_max')

        # 转换为范围
        if size_min and size_max:
            size_range = (size_min, size_max)
        elif size_min:
            size_range = (size_min, '∞')  # 代表无上限
        elif size_max:
            size_range = ('0', size_max)  # 代表无下限
        else:
            size_range = None

        datasets = DatasetRepository.search(
            name=name, path=path, cuda=cuda, size_range=size_range
        )
        print(f"Query result: {datasets}")  # 打印查询结果
        return [dataset.to_dict() for dataset in datasets]


# 注册命名空间
api.add_namespace(datasets_ns)
