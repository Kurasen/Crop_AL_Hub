import json

from flask import request, send_file, Blueprint, make_response

from app.exts import db
from app.schemas.model_schema import ModelRunSchema, ModelTestSchema, ModelSearchSchema, ModelCreateSchema, \
    ModelUpdateSchema
from app.utils.json_encoder import create_json_response
from app.model.model_service import ModelService

# 设置允许的文件格式
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}

# 定义命名空间：模型
models_bp = Blueprint('models', __name__, url_prefix='/api/v1/models')


# 定义 run_model 接口，接收模型编号和数据集编号
@models_bp.route('/<int:model_id>/run', methods=['GET'])
def run(model_id):
    """
    通过模型ID和数据集ID运行模型，并返回模型的训练准确率。
    参数：模型ID和数据集ID
    """
    # 获取请求参数中的模型编号和数据集编号
    dataset_id = ModelRunSchema().load(request.args).get('dataset_id')

    model_accuracy_info = ModelService.get_model_accuracy(model_id, dataset_id)
    return create_json_response(model_accuracy_info)


# 接收图片并返回处理后的图片和 JSON
@models_bp.route('/<int:model_id>/test-model', methods=['POST'])
def test_model(model_id):
    """
    上传一张图片，进行处理并返回处理后的图片和相应的 JSON 数据。
    """
    # 文件校验
    uploaded_file = ModelTestSchema().load(request.files).get('file')

    # 处理模型和文件，获取图像处理路径和模型信息
    processed_image_path, model_info = ModelService.process_model_and_file(model_id, uploaded_file)

    # 构造响应
    response = make_response(send_file(
        processed_image_path,
        mimetype='image/jpeg'
    ))

    response.headers['X-Model-Output'] = json.dumps(model_info)

    return response


@models_bp.route('', methods=['GET'])
def search():
    """
    通过模型名称、输入类型、是否支持CUDA等条件来搜索模型。
    支持分页查询，并返回模型的详细信息。
    示例请求：
    ?name=example&input=image&cuda=true&describe=good&size_min=100MB&size_max=1GB&page=1&per_page=10
    """
    search_params = ModelSearchSchema().load(request.args.to_dict())
    result = ModelService.search_models(search_params)
    return create_json_response(result)


@models_bp.route('', methods=['POST'])
def create_model():
    """
    创建新模型
    """
    # 获取请求数据
    model_instance = ModelCreateSchema().load(request.get_json(), session=db.session)
    result, status = ModelService.create_model(model_instance)
    return create_json_response(result, status)


@models_bp.route('/<int:model_id>', methods=['GET'])
def get_model(model_id):
    """
    获取特定模型的详细信息
    """
    model = ModelService.get_model_by_id(model_id)
    return create_json_response(model.to_dict())


@models_bp.route('/<int:model_id>', methods=['PUT'])
def update_model(model_id):
    """
    更新现有模型
    """
    model = ModelService.get_model_by_id(model_id)
    updates = request.get_json()
    model_instance = ModelUpdateSchema().load(
        updates,
        instance=model,  # 传入现有实例
        partial=True,  # 允许部分更新
        session=db.session,
    )
    updated_model, status = ModelService.update_model(model_instance)
    return create_json_response(updated_model, status)


@models_bp.route('/<int:model_id>', methods=['DELETE'])
def delete_model(model_id):
    """
    删除现有模型
    """
    response, status = ModelService.delete_model(model_id)
    return create_json_response(response, status)
