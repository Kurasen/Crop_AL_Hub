from flask import Blueprint, jsonify, request
from flask_restx import Api, Resource, fields

# 创建蓝图
models_bp = Blueprint('models', __name__, url_prefix='/models')

# 创建 API 对象
api = Api(models_bp, version='1.0', title='Flask Models API', description='Retrieve models')

# 定义命名空间：模型
models_ns = api.namespace('models',description='Operations models')

# 模拟数据函数：模型数据
def get_mock_models():
    return [{"id": i, "name": f"Model_{i}"} for i in range(1, 11)]

# 获取模型列表的接口
@models_ns.route('/list')
class ModelsResource(Resource):
    @api.doc(description='Retrieve a list of models')
    def get(self):
        # 返回模拟的模型数据
        return jsonify(get_mock_models())

# 定义 run_model 接口，接收模型编号和数据集编号
@models_ns.route('/run')
class RunModelResource(Resource):
    @api.doc(description='Run the model with the dataset and return the accuracy')
    @api.param('model_id', 'Model ID to use')
    @api.param('dataset_id', 'Dataset ID to use')
    def post(self):
        # 获取请求参数中的模型编号和数据集编号
        model_id = request.args.get('model_id', type=int)
        dataset_id = request.args.get('dataset_id', type=int)

        # 根据模型和数据集编号生成模拟的准确率
        if model_id and dataset_id:
            accuracy = f"Model_{model_id} trained on Dataset_{dataset_id} has an accuracy of {model_id * dataset_id}%"
            return jsonify({"accuracy": accuracy})  # 使用 jsonify 返回有效的 JSON 响应
        else:
            return jsonify({"error": "Model ID and Dataset ID are required"}), 400  # 错误时返回 400 状态码