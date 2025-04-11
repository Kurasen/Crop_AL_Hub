import uuid
from datetime import datetime
from flask import Blueprint, g

from app import Model
from app.core.exception import FileUploadError
from app.docker.core.storage import FileStorage, cleanup_directory
from app.exts import db
from app.model.model_repo import ModelRepository
from app.schemas.model_schema import ModelRunSchema, ModelSearchSchema, ModelCreateSchema, \
    ModelUpdateSchema

from flask import request
from app.config import Config
from app.docker.core.docker_clinet import docker_client
from app.docker.core.task import logger, run_algorithm
from app.model.model_service import ModelService
from app.token.JWT import admin_required, auth_required, resource_owner
from app.utils import create_json_response
from app.utils.common.common_service import CommonService

# 设置允许的文件格式
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}

# 定义命名空间：模型
models_bp = Blueprint('models', __name__, url_prefix='/api/v1/models')


# 定义 run_model 接口，接收模型编号和数据集编号
@models_bp.route('/<int:model_id>/run', methods=['GET'])
@auth_required
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
    types = CommonService.get_all_types(ModelRepository)
    return create_json_response({
        "data": {"types": types}
    })


@models_bp.route('', methods=['POST'])
@admin_required
def create_model():
    """
    创建新模型
    """
    request_data = request.get_json()
    request_data['user_id'] = g.current_user.id
    model_instance = ModelCreateSchema().load(request_data, session=db.session)
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
@resource_owner(model=Model, id_param='model_id')
def update_model(instance):
    """
    更新现有模型
    """
    updates = request.get_json()
    model_instance = ModelUpdateSchema().load(
        updates,
        instance=instance,  # 传入现有实例
        partial=True,  # 允许部分更新
        session=db.session,
    )
    updated_model, status = ModelService.update_model(model_instance)
    return create_json_response(updated_model, status)


@models_bp.route('/<int:model_id>', methods=['DELETE'])
@resource_owner(model=Model, id_param='model_id')
def delete_model(instance):
    """
    删除现有模型
    """
    response, status = ModelService.delete_model(instance)
    return create_json_response(response, status)


@models_bp.before_request
def log_request():
    print(f"Request started at: {datetime.now()}")


# Flask路由：上传文件并触发任务
@models_bp.route('/<int:model_id>/test-model', methods=['POST'])
@auth_required
def process_image(model_id):
    # 查数据库，获取对应的 image_name
    model = ModelService.get_model_by_id(model_id)
    image_name = model.image
    instruction = model.instruction

    # 校验镜像是否存在
    docker_client.validate_image(image_name)

    # 生成任务id
    task_id = str(uuid.uuid4())

    file = request.files.get('file')
    if not file or file.filename == '':
        raise FileUploadError("未上传任何文件")

    uploaded_files = [file]
    # # 获取并验证图片URL
    # image_url = request.form.get('url')
    # if not image_url:
    #     raise ValidationError("必须提供图片URL参数")
    #
    # # URL格式验证（严格匹配服务器路径）
    # if not image_url.startswith(FileConfig.FILE_BASE_URL):
    #     raise ValidationError("仅支持访问本机服务器文件资源")
    #
    # # 路径转换和安全验证
    # parsed_url = urlparse(image_url)
    # server_relative_path = parsed_url.path.split("/file", 1)[-1].lstrip('/')
    #
    # # 配置本地存储基础路径
    # LOCAL_FILE_BASE = Path(FileConfig.LOCAL_FILE_BASE)
    # local_full_path = LOCAL_FILE_BASE / server_relative_path
    #
    # # 安全校验（防止路径遍历）
    # try:
    #     if not local_full_path.resolve().is_relative_to(LOCAL_FILE_BASE.resolve()):
    #         raise SecurityError("非法路径访问尝试")
    # except FileNotFoundError:
    #     raise FileNotFoundError(f"路径不存在: {local_full_path}")
    #
    # # 文件存在性检查
    # if not local_full_path.is_file():
    #     raise FileNotFoundError(f"指定文件不存在: {local_full_path}")
    #
    # # 使用自定义类进行文件校验
    # try:
    #     FileStorage.is_file_corrupted(local_full_path)  # 前置损坏检查
    # except ImageProcessingError as e:
    #     raise FileValidationError(f"文件损坏验证失败: {str(e)}")
    #
    # # 创建文件对象（适配后续处理）
    # with open(local_full_path, 'rb') as f:
    #     # 创建符合预期的文件对象
    #     file_obj = type('', (object,), {
    #         'filename': local_full_path.name,
    #         'read': f.read,
    #         'stream': f
    #     })()
    #
    #     # 使用自定义方法保存文件
    #     try:
    #         saved_dir = FileStorage.upload_input(
    #             file=file_obj,
    #             image_name=model.image,
    #             task_id=task_id
    #         )
    #     except Exception as e:
    #         logger.error(f"文件保存失败: {str(e)}")
    #         raise FileSaveError("文件存储过程失败")

    # # 后续处理（保持原有逻辑）
    # uploaded_files = [file_obj]

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
        message = '任务处理失败，请重新上传数据或联系系统管理员'
        status_code = 500  # 500 Internal Server Error - 任务执行失败
        logger.error("error: %s", error_message)
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
