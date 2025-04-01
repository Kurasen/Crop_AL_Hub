import json
import uuid
from datetime import datetime

from flask import send_file, Blueprint, make_response
from app.core.exception import ValidationError, FileUploadError
from app.docker.core.storage import FileStorage, cleanup_directory
from app.exts import db
from app.schemas.model_schema import ModelRunSchema, ModelTestSchema, ModelSearchSchema, ModelCreateSchema, \
    ModelUpdateSchema
from pathlib import Path
from flask import request, jsonify
from app.config import Config
from app.docker.core.docker_clinet import docker_client
from app.docker.core.task import logger, run_algorithm
from app.model.model_service import ModelService
from app.utils import create_json_response
from docker.errors import ImageNotFound

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


@models_bp.before_request
def log_request():
    print(f"Request started at: {datetime.now()}")


# Flask路由：上传文件并触发任务
@models_bp.route('/<int:model_id>/test-model', methods=['POST'])
def process_image(model_id):
    # 查数据库，获取对应的 image_name
    model = ModelService.get_model_by_id(model_id)
    image_name = model.image
    instruction = model.instruction

    # 校验镜像是否存在
    docker_client.validate_image(image_name)

    # 生成任务id
    task_id = str(uuid.uuid4())

    file = ModelTestSchema().load(request.files).get('file')
    if file is None:
        return create_json_response({"error": "未上传图片"}, status=400)
    uploaded_files = [file]

    # 保存所有文件到同一目录（只需保存第一个文件即可获取目录路径）
    try:
        if len(uploaded_files) == 0:
            raise FileUploadError("未上传任何文件")

        # 保存第一个文件并获取目录路径
        first_file = uploaded_files[0]
        target_dir = FileStorage.upload_input(first_file, image_name, task_id)

        # 保存剩余文件到同一目录
        for file in uploaded_files[1:]:
            FileStorage.save_upload(
                file_stream=file,
                save_dir=target_dir,  # 使用已创建的目录
                file_name=file.filename
            )
    except Exception as e:
        logger.error(f"文件保存失败: {str(e)}")
        return create_json_response({'error': {"message": '服务器异常，文件保存失败'}}, 500)

    output_folder = Config.OUTPUT_FOLDER
    output_dir = output_folder / image_name / f"task_{task_id}"
    task = run_algorithm.apply_async(
        args=(str(target_dir), task_id, image_name, instruction),
        task_id=task_id
    )

    cleanup_directory.apply_async(
        args=(str(target_dir), str(output_dir)),
        countdown=86400  # 1天 = 60*60*24 秒
    )

    return create_json_response({
        "data": {
            'task_id': task_id,
        },
        "message": "任务提交成功",
    }), 202


# Flask路由：查询任务状态
@models_bp.route('/task/<task_id>', methods=['GET'])
def get_task_status(task_id):
    task = run_algorithm.AsyncResult(task_id)
    # 判断任务状态
    if task.state == 'PENDING':
        response = {'result': {"status": "PENDING"}}  # 如果任务还在等待中，不返回结果
        message = '任务尚未开始处理'
        status_code = 202  # 202 Accepted - 请求已接受，正在处理
    elif task.state == 'STARTED':
        response = {'result': {"status": "STARTED"}}  # 任务已开始但未完成
        message = '任务正在处理中，请耐心等待'
        status_code = 202  # 200 OK - 请求成功，任务正在处理中
    elif task.state == 'SUCCESS':
        response = {'result': task.result}  # 返回任务结果
        message = '任务处理成功'
        status_code = 200  # 200 OK - 请求成功，任务完成
    elif task.state == 'FAILURE':
        error_message = str(task.info)
        response = {'result': {"status": "FAILURE"}}
        message = f'任务处理失败，请重新上传数据或联系系统管理员: {error_message}'
        status_code = 500  # 500 Internal Server Error - 任务执行失败
    elif task.state == 'RETRY':
        response = {'result': {"status": "RETRY"}}  # 返回任务结果
        message = '运行过程中发生错误，任务正在重试中'
        status_code = 202
    else:
        response = {'result': None}  # 其他状态
        message = f'当前状态: {task.state}'
        status_code = 500  # 500 Internal Server Error - 未知错误状态

    # 返回统一格式的响应
    return create_json_response({
        'data': response,
        'message': message,
    }, status_code)
