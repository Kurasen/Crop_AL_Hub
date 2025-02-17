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


# 从数据库获取模型数据
def get_all_models():
    # 从数据库查询所有模型
    models = Model.query.all()
    if not models:
        raise DatabaseError("No datasets found in the database")
    return [model.to_dict() for model in models]


# 检查文件扩展名是否有效
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# 处理模型输出的 JSON 数据（可以根据不同模型返回不同字段）
def generate_mock_json(model_id):
    # 这里只是模拟，不同模型的输出可以有所不同
    return {
        'model_id': model_id,
        'accuracy': 92.5,
        'description': f'Model {model_id} processed the image successfully.'
    }


# 获取模型列表的接口
@models_bp.route('/list', methods=['GET'])
def list():
    """
    获取所有模型的信息列表，包括模型ID、名称、图片、输入类型等。
    返回的模型列表将包括每个模型的描述、是否支持CUDA等信息。
    """
    models = get_all_models()
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

    model = ModelService.get_model_by_id(model_id)
    dataset = DatasetService.get_dataset_by_id(dataset_id)

    # 如果模型或数据集不存在，则返回错误信息
    if not model:
        raise ValidationError(f"Model with ID {model_id} not found")
    if not dataset:
        raise ValidationError(f"Dataset with ID {dataset_id} not found")

    accuracy = f"Model_{model_id} trained on Dataset_{dataset_id} has an accuracy of {model_id * dataset_id}%"
    return jsonify({"accuracy": accuracy})


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

        try:
            # 尝试将 model_id 转换为整数
            model_id = int(model_id)
        except ValueError:
            raise ValidationError("model_id 应该是整数类型")

        # 检查 model_id 是否有效
        if not ModelService.get_model_by_id(model_id):
            raise ValidationError("无效的 model_id")

        # 处理模型和文件，获取图像处理路径和模型信息
        processed_image_path, model = ModelService.handle_model_and_file(model_id, uploaded_file)

        # 构造响应
        response = make_response(send_file(
            processed_image_path,
            mimetype='image/jpeg'
        ))
        response.headers['X-Model-Output'] = json.dumps({
            'model_id': model_id,
            'accuracy': 92.5,
            'description': f'Model {model_id} processed successfully'
        })

    except ValidationError as e:
        current_app.logger.error(f"Validation Error during registration: {str(e)}")
        raise e
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
