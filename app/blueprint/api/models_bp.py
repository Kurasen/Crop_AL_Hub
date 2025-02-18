import json
import os

from flask import jsonify, request, send_file, after_this_request, Blueprint, Response, make_response, current_app
from flask_restx import Resource, fields, reqparse, Namespace
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app.blueprint.utils.JSONEncoder import CustomJSONEncoder, create_json_response
from app.exception.errors import ValidationError, DatabaseError
from app.models.model import Model
from app.services.dataset_service import DatasetService
from app.services.model_service import ModelService

# 定义排序字段的枚举类型（例如：stars, size, etc.）
SORT_BY_CHOICES = ['accuracy', 'sales', 'stars', 'likes']
# 定义排序顺序的枚举类型（升序或降序）
SORT_ORDER_CHOICES = ['asc', 'desc']
# 设置允许的文件格式
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}

# 定义命名空间：模型
models_bp = Blueprint('models', __name__)

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
UPLOAD_FOLDER = os.path.join(project_root, 'test')  # 定位到 'test' 文件夹


# 获取模型列表的接口
@models_bp.route('/list', methods=['GET'])
def list():
    """
    获取所有模型的信息列表，包括模型ID、名称、图片、输入类型等。
    返回的模型列表将包括每个模型的描述、是否支持CUDA等信息。
    """
    models = ModelService.get_all_models()
    return create_json_response(models)


# 定义 run_model 接口，接收模型编号和数据集编号
@models_bp.route('/run', methods=['GET'])
def run():
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

    try:
        accuracy = ModelService.get_model_accuracy(model_id, dataset_id)
        return jsonify({"accuracy": accuracy})
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400


# 接收图片并返回处理后的图片和 JSON
@models_bp.route('/test_model', methods=['POST'])
def test_model():
    """
    上传一张图片，进行处理并返回处理后的图片和相应的 JSON 数据。
    """
    try:
        model_id = request.form.get('model_id')
        if not model_id or model_id == '':
            raise ValidationError("未提供 model_id")

        # 文件校验
        uploaded_file = request.files.get('file')
        if not uploaded_file or uploaded_file.filename == '':
            raise ValidationError("未上传文件或未选择文件")

        # 处理模型和文件，获取图像处理路径和模型信息
        processed_image_path, model_info = ModelService.process_model_and_file(model_id, uploaded_file)

        # 构造响应
        response = make_response(send_file(
            processed_image_path,
            mimetype='image/jpeg'
        ))
        response.headers['X-Model-Output'] = json.dumps(model_info)

        return response

    except Exception as e:
        return create_json_response(str(e), 500)


@models_bp.route('/search', methods=['GET'])
def search():
    """
    通过模型名称、输入类型、是否支持CUDA等条件来搜索模型。
    支持分页查询，并返回模型的详细信息。
    示例请求：
    ?name=example&input=image&cuda=true&describe=good&size_min=100MB&size_max=1GB&page=1&per_page=10
    """
    # 获取查询参数
    name = request.args.get('name')
    input = request.args.get('input')
    cuda = request.args.get('cuda', type=lambda v: v.lower() == 'true')  # Properly handle 'cuda' param
    description = request.args.get('description')
    type = request.args.get('type')
    sort_by = request.args.get('sort_by', default='stars')  # 默认排序字段
    sort_order = request.args.get('sort_order', default='asc')  # 默认排序顺序
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 5))

    # 调用 ModelService 的 search_models 方法
    result = ModelService.search_models(
        name=name,
        input=input,
        cuda=cuda,
        description=description,
        type=type,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        per_page=per_page
    )

    return create_json_response(result)
