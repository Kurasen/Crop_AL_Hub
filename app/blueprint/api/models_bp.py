
import json
import os

from flask import Blueprint, jsonify, request, send_file, after_this_request, Response, make_response
from flask_restx import Api, Resource, fields, reqparse
from werkzeug.datastructures import FileStorage

from app.models.model import Model

# 创建蓝图
models_bp = Blueprint('models', __name__, url_prefix='/models')

# 创建 API 对象
api = Api(models_bp, version='1.0', title='Flask Models API', description='Retrieve models')

# 定义命名空间：模型
models_ns = api.namespace('models',description='Operations models')

# 定义上传的文件模型
models_model = api.model('ImageUpload', {
    'id': fields.Integer(description='Model ID'),
    'name': fields.String(description='Model Name'),
    'image': fields.String(description='Model Image'),
    'input': fields.String(description='Model Input'),
    'describe': fields.String(description='Model Description'),
    'cuda': fields.Boolean(description='CUDA Support'),
    'instruction': fields.String(description='Model Instruction')
})


# 注册模型
api.models['ImageUpload'] = models_model

# 定义文件上传字段
upload_parser = reqparse.RequestParser()
upload_parser.add_argument('file', type=FileStorage, location='files', required=True, help='上传图片文件')

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
UPLOAD_FOLDER = os.path.join(project_root, 'test')  # 定位到 'test' 文件夹

# 从数据库获取模型数据
def get_all_models():
    # 从数据库查询所有模型
    models = Model.query.all()
    return [{
        'id': model.id,
        'name': model.name,
        'image': model.image,
        'input': model.input,
        'describe': model.describe,
        'cuda': model.cuda,
        'instruction': model.instruction
    } for model in models]


# 模拟的图像处理函数
def process_image(image_file):
     return image_file

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
    @api.marshal_with(models_model, as_list=True)  # 标明返回是一个数据集列表
    def get(self):
        # 返回模拟的模型数据
        return get_all_models()

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
    @api.doc(description='上传图片，处理后返回处理结果和 JSON 响应')
    @api.expect(upload_parser)  # 使用 reqparse 定义的 parser
    def post(self):
        # 使用 reqparse 获取上传的图片文件
        args = upload_parser.parse_args()
        uploaded_file = args.get('file')

        if not uploaded_file:
            return {'message': '未上传文件'}, 400

        # 确保上传文件目录存在
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)

        # 保存上传的文件到指定文件夹
        file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.filename)
        # 保存文件
        uploaded_file.save(file_path)

        # 模拟的图像处理：在这里只是返回原图，假装做了处理
        processed_image_path = process_image(file_path)

        # 生成模型输出的 JSON 数据（你可以根据需要修改）
        model_output_json = {
            'model_id': 1,
            'accuracy': 92.5,
            'description': f'Model 1 processed the image successfully.'
        }

        # 将模型输出 JSON 添加到响应头部
        @after_this_request
        def add_json_response(response):
            response.headers['X-Model-Output'] = json.dumps(model_output_json)
            return response

        # 返回“假装处理”后的图片
        return send_file(processed_image_path, mimetype='image/jpeg', as_attachment=True, download_name=uploaded_file.filename)

# # 接收图片并返回处理后的 JSON
# @models_ns.route('/test_model')
# class GetResultResource(Resource):
#     @api.doc(description='获取模型处理结果的 JSON 响应')
#     @api.expect(upload_parser)  # 使用 reqparse 定义的 parser
#     def post(self):
#         # 使用 reqparse 获取文件
#         args = upload_parser.parse_args()
#         uploaded_file = args.get('file')
#
#         if not uploaded_file:
#             return {'message': '未上传文件'}, 400
#
#         # 处理上传的文件
#         processed_image = process_image(uploaded_file)
#         model_output_json = generate_mock_json(model_id=1)
#
#         # 返回模型输出的 JSON 数据
#         return jsonify(model_output_json)
## 接收图片并返回处理后的图片
# @models_ns.route('/test_model/download_image')
# class DownloadImageResource(Resource):
#     @api.doc(description='上传图片并返回处理后的图片文件')
#     @api.expect(upload_parser)  # 使用 reqparse 定义的 parser
#     def post(self):
#         # 使用 reqparse 获取文件
#         args = upload_parser.parse_args()
#         uploaded_file = args.get('file')
#
#         if not uploaded_file:
#             return {'message': '未上传文件'}, 400
#
#         # 处理上传的文件
#         processed_image = process_image(uploaded_file)
#
#         # 将处理后的图片保存到内存
#         img_io = processed_image
#         img_io.seek(0)
#
#         # 返回处理后的图片
#         return send_file(img_io, mimetype='image/png', as_attachment=True, download_name='processed_image.png')