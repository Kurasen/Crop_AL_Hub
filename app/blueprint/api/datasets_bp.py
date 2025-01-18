from flask import Blueprint, jsonify
from flask_restx import Api, Resource, fields

from app.models.dataset import Dataset

# 创建蓝图
datasets_bp = Blueprint('datasets', __name__, url_prefix='/datasets')

# 创建 API 对象
api = Api(datasets_bp,version='1.0',title='Flask Datasets API',description='Retrieve datasets')

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