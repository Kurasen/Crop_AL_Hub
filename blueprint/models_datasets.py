from flask import Blueprint, jsonify
from flask_restx import Api, Resource, fields

# 创建蓝图
models_datasets_bp = Blueprint('models_datasets', __name__)

# 创建 API 对象
api = Api(models_datasets_bp, version='1.0', title='Flask Models and Datasets API', description='Retrieve models and datasets', doc='/swagger-ui')

# 模拟数据函数：模型数据
def get_mock_models():
    return [{"id": i, "name": f"Model_{i}"} for i in range(1, 11)]

# 模拟数据函数：数据集数据
def get_mock_datasets():
    return [{"id": i, "name": f"Dataset_{i}"} for i in range(1, 11)]

# 定义命名空间：模型
models_ns = api.namespace('models', description='Operations related to models')

# 定义命名空间：数据集
datasets_ns = api.namespace('datasets', description='Operations related to datasets')

# 获取模型列表的接口
@models_ns.route('/')
class ModelsResource(Resource):
    @api.doc(description='Retrieve a list of models')
    def get(self):
        # 返回模拟的模型数据
        return jsonify(get_mock_models())

# 获取数据集列表的接口
@datasets_ns.route('/')
class DatasetsResource(Resource):
    @api.doc(description='Retrieve a list of datasets')
    def get(self):
        # 返回模拟的数据集数据
        return jsonify(get_mock_datasets())
