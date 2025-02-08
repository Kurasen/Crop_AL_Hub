import json
import os

from flask import jsonify, request, send_file, after_this_request
from flask_restx import Resource, fields, reqparse, Namespace
from werkzeug.datastructures import FileStorage

from app.exception.errors import ValidationError
from app.models.model import Model
from app.services.model_service import ModelService


# 定义命名空间：模型
models_ns = Namespace('models', description='Operations models')

# 定义上传的文件模型
models_model = models_ns.model('ImageUpload', {
    'id': fields.Integer(description='Model ID'),
    'name': fields.String(description='Model Name'),
    'image': fields.String(description='Model Image'),
    'input': fields.String(description='Model Input'),
    'describe': fields.String(description='Model Description'),
    'cuda': fields.Boolean(description='CUDA Support'),
    'instruction': fields.String(description='Model Instruction')
})

# 注册模型
models_ns.models['ImageUpload'] = models_model

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
        'describe': model.description,
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
    @models_ns.doc(description='Retrieve a list of models')
    @models_ns.marshal_with(models_model, as_list=True)  # 标明返回是一个数据集列表
    def get(self):
        """
        获取所有模型的信息列表，包括模型ID、名称、图片、输入类型等。
        返回的模型列表将包括每个模型的描述、是否支持CUDA等信息。
        """
        return get_all_models()


# 定义 run_model 接口，接收模型编号和数据集编号
@models_ns.route('/run')
class RunModelResource(Resource):
    @models_ns.doc(description='Run the model with the dataset and return the accuracy')
    @models_ns.param('dataset_id', 'Dataset ID to use')
    @models_ns.param('model_id', 'Model ID to use')
    def post(self):
        """
        通过模型ID和数据集ID运行模型，并返回模型的训练准确率。
        参数：模型ID和数据集ID
        """
        # 获取请求参数中的模型编号和数据集编号
        model_id = request.args.get('model_id', type=int)
        dataset_id = request.args.get('dataset_id', type=int)

        # 根据模型和数据集编号生成模拟的准确率
        if not model_id or not dataset_id:
            raise ValidationError("Model ID and Dataset ID are required")  # 参数缺失时抛出 ValidationError

        accuracy = f"Model_{model_id} trained on Dataset_{dataset_id} has an accuracy of {model_id * dataset_id}%"
        return jsonify({"accuracy": accuracy})


# 接收图片并返回处理后的图片和 JSON
@models_ns.route('/test_model')
class TestModelResource(Resource):
    @models_ns.doc(description='上传图片，处理后返回处理结果和 JSON 响应')
    @models_ns.expect(upload_parser)  # 使用 reqparse 定义的 parser
    def post(self):
        """
        上传一张图片，进行处理并返回处理后的图片和相应的 JSON 数据。
        """
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
        return send_file(processed_image_path, mimetype='image/jpeg', as_attachment=True,
                         download_name=uploaded_file.filename)


@models_ns.route('/search')
class ModelSearchResource(Resource):
    @models_ns.doc(description='Search for models by name, input type, or CUDA support')
    @models_ns.param('cuda', 'CUDA support (True or False)')
    @models_ns.param('input', 'Input type of the model to search')
    @models_ns.param('describe', 'Describe of the model to search')
    @models_ns.param('name', 'Name of the model to search')
    @models_ns.marshal_with(models_model, as_list=True)
    def get(self):
        """
        通过模型名称、输入类型、是否支持CUDA等条件来搜索模型。
        支持分页查询，并返回模型的详细信息。
        示例请求：
        ?name=example&input=image&cuda=true&describe=good&size_min=100MB&size_max=1GB&page=1&per_page=10
        """
        # 获取查询参数
        name = request.args.get('name')
        input_type = request.args.get('input')
        cuda = request.args.get('cuda', type=lambda v: v.lower() == 'true')  # Properly handle 'cuda' param
        describe = request.args.get('describe')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))

        # 打印解析后的参数
        print(f"Parsed Parameters - Name: {name}, Input: {input_type}, CUDA: {cuda},Describe：{describe}, Page: {page}, Per Page: {per_page}")

        # 调用 ModelService 的 search_models 方法

        result = ModelService.search_models(
            search_term=name,
            input_type=input_type,
            cuda=cuda,
            describe=describe,
            page=page,
            per_page=per_page
        )

        print(f"Query result: {result}")
        return result['data'], 200


