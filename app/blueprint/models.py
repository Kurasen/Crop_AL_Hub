import io
import json

from PIL import Image
from flask import Blueprint, jsonify, request, send_file
from flask_restx import Api, Resource, fields

# 创建蓝图
models_bp = Blueprint('models', __name__, url_prefix='/models')

# 创建 API 对象
api = Api(models_bp, version='1.0', title='Flask Models API', description='Retrieve models')

# 定义命名空间：模型
models_ns = api.namespace('models',description='Operations models')

# 定义上传的文件模型
models_model = api.model('ImageUpload', {
    'file': fields.String(required=True, description='Upload image file', type='file')
})

# 注册模型
api.models['ImageUpload'] = models_model

# 模拟数据函数：模型数据
def get_mock_models():
    return [{"id": i, "name": f"Model_{i}"} for i in range(1, 11)]

# 模拟的图像处理函数
def process_image(image_file):
    # 使用 Pillow 处理图片（这里只是简单的打开并转为灰度）
    image = Image.open(image_file)
    image = image.convert('L')  # 转为灰度图

    # 将处理后的图片保存到内存
    img_io = io.BytesIO()
    image.save(img_io, 'PNG')  # 保存为 PNG 格式
    img_io.seek(0)  # 返回指针到文件开头
    return img_io

# 处理模型输出的 JSON 数据（可以根据不同模型返回不同字段）
def generate_mock_json(model_id):
    # 这里只是模拟，不同模型的输出可以有所不同
    return {
        'model_id': model_id,
        'accuracy': 92.5,
        'description': f'Model {model_id} processed the image successfully.'
    }


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
    @api.param('dataset_id', 'Dataset ID to use')
    @api.param('model_id', 'Model ID to use')
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

# 接收图片并返回处理后的图片和 JSON
@models_ns.route('/test_model')
class TestModelResource(Resource):
    @api.doc(description='Upload an image, process it, and return the processed image and a JSON response.')
    @api.expect(models_model)
    def post(self):
        # 获取上传的文件
        file = request.files.get('file')

        if not file:
            return {'message': 'No file uploaded'}, 400

        # 模拟处理模型（模型 ID 这里用 1）
        processed_image = process_image(file)
        model_output_json = generate_mock_json(model_id=1)

        # 返回处理后的图片和 JSON 响应
        # 注意：这里无法直接返回文件和 JSON 一起，但可以使用自定义返回格式或返回头
        return send_file(processed_image, mimetype='image/png', download_name='processed_image.png', as_attachment=True)