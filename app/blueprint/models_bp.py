import json

from flask import send_file, Blueprint, make_response


from app.exts import db
from app.schemas.model_schema import ModelRunSchema, ModelTestSchema, ModelSearchSchema, ModelCreateSchema, \
    ModelUpdateSchema

# 设置允许的文件格式
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}

# 定义命名空间：模型
models_bp = Blueprint('models', __name__, url_prefix='/api/v1/models')


# 定义 run_model 接口，接收模型编号和数据集编号
@models_bp.route('/<int:model_id>/run', methods=['GET'])
# @token_required
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
# @token_required
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
# @token_required
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


@models_bp.route('/types', methods=['GET'])
def get_all_types():
    """获取所有唯一的模型类型列表"""
    types = ModelService.get_all_types()
    return create_json_response({
        "data": {"types": types}
    })


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
    return create_json_response({
        "data": model.to_dict()
    })


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


import uuid
from pathlib import Path

import docker
from flask import request, jsonify

from app.config import Config
from app.docker.core.docker_clinet import docker_client
from app.docker.core.task import logger, run_algorithm
from app.model.model_service import ModelService
from app.utils import create_json_response
from docker.errors import ImageNotFound


# Flask路由：上传文件并触发任务
@models_bp.route('/process', methods=['POST'])
def process_image():
    # 获取前端传递的model_id
    model_id = request.form.get('model_id')

    try:
        model_id = int(model_id)
    except ValueError:
        return jsonify({'error': 'model_id必须是整数'}), 400

    # 查数据库，获取对应的 image_name
    model = ModelService.get_model_by_id(model_id)
    image_name = model.image

    # 校验镜像是否存在
    try:
        docker_client.client.images.get(image_name)
    except docker.errors.ImageNotFound:
        return jsonify({'error': f'镜像 {image_name} 未找到，请先拉取镜像'}), 400
    except docker.errors.APIError as e:
        logger.error(f"Docker服务异常: {str(e)}")
        return jsonify({'error': 'Docker服务不可用'}), 50

    if 'file' not in request.files:
        return jsonify({'error': '未上传文件d'}), 400

    file = request.files['file']

    # 生成符合Docker规范的宿主机路径
    task_id = str(uuid.uuid4())
    input_subdir = f"task_{task_id}"

    # 使用绝对路径（关键修改）
    host_upload_dir = Path(Config.UPLOAD_FOLDER) / input_subdir
    host_upload_dir.mkdir(parents=True, exist_ok=True)

    # 保存文件
    file_path = host_upload_dir / file.filename
    file.save(file_path)
    logger.info(f"文件保存位置: {file_path}")

    # 提交任务时传递绝对路径
    task = run_algorithm.delay(str(host_upload_dir), task_id, image_name)

    return create_json_response({
        "data": {
            'task_id': task.id,
            'image_used': image_name,  # 返回使用的镜像信息
        },
        "message": "任务提交成功",
    }, 202)


# Flask路由：查询任务状态
@models_bp.route('/task/<task_id>', methods=['GET'])
def get_task_status(task_id):
    task = run_algorithm.AsyncResult(task_id)
    # 判断任务状态
    if task.state == 'PENDING':
        response = {'result': None}  # 如果任务还在等待中，不返回结果
        message = '任务尚未开始处理'
    elif task.state == 'SUCCESS':
        response = {'result': task.result}  # 返回任务结果
        message = '任务处理成功'
    elif task.state == 'FAILURE':
        response = {'result': task.result}  # 如果任务失败，返回无结果
        message = f'任务处理失败: {str(task.info)}'
    else:
        response = {'result': None}  # 其他状态
        message = f'当前状态: {task.state}'

    # 返回统一格式的响应
    return create_json_response({
        'data': response,
        'message': message,
    })
