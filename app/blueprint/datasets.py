from flask import Blueprint, jsonify
from flask_restx import Api, Resource, fields

# 创建蓝图
datasets_bp = Blueprint('datasets', __name__, url_prefix='/datasets')

# 创建 API 对象
api = Api(datasets_bp,version='1.0',title='Flask Datasets API',description='Retrieve datasets')

# 定义命名空间：数据集
datasets_ns = api.namespace('datasets', description='Operations related to datasets')

# 定义数据集的模型
dataset_model = api.model('Dataset', {
    'id': fields.Integer(required=True, description='Dataset ID'),
    'name': fields.String(required=True, description='Dataset Name'),
    'description': fields.String(description='Dataset Description')
})

# 注册模型
api.models['Dataset'] = dataset_model  # 注册模型

# 模拟数据函数：数据集数据
def get_mock_datasets():
    return [
        {"id": i, "name": f"Dataset_{i}", "description": f"This is Dataset_{i}"}
        for i in range(1, 11)
    ]

# 获取数据集列表的接口
@datasets_ns.route('/list')
class DatasetsResource(Resource):
    @api.doc(description='Retrieve a list of datasets')
    @api.marshal_with(dataset_model, as_list=True)  # 标明返回是一个数据集列表
    def get(self):
        # 返回模拟的数据集数据
        return get_mock_datasets()