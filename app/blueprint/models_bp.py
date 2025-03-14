import json

from flask import send_file, Blueprint, make_response, request


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



# # app/routes/api.py
# from flask import Blueprint, request, jsonify
# from uuid import uuid4
# from app.docker.file_util import save_uploaded_file
# from app.docker.task import Task
# from app.docker.docker_service import run_algorithm
#
# @models_bp.route("/run/<algorithm_name>", methods=["POST"])
# def run_algorithm_route(algorithm_name: str):
#     # 1. 生成唯一任务ID
#     task_id = str(uuid4())
#
#     # 2. 保存上传的文件
#     if "image" not in request.files:
#         return jsonify({"error": "No file uploaded"}), 400
#     file = request.files["image"]
#     save_uploaded_file(file, task_id)
#
#     # 3. 创建任务记录
#     Task.create_task(task_id, algorithm_name)
#
#     # 4. 启动Docker容器
#     try:
#         run_algorithm(task_id, algorithm_name)
#         Task.update_status(task_id, "running")
#     except Exception as e:
#         Task.update_status(task_id, "failed")
#         return jsonify({"error": str(e)}), 500
#
#     return jsonify({"task_id": task_id}), 202
#
# @models_bp.route("/task/<task_id>", methods=["GET"])
# def get_task_status(task_id: str):
#     # 从Redis中获取任务状态
#     status = Task.get_status(task_id)
#     return jsonify({"task_id": task_id, "status": status})
#
# #
# import os
# import uuid
# from flask import Flask, request, jsonify
# from redis import Redis
#
# redis_client = Redis(host='localhost', port=6379, db=0)
# TASK_BASE_DIR = '/tmp/tasks'
# #优化点：要符合restful设计，前端应该有个上传图片和选择框选择算法，
# @models_bp.route('/upload', methods=['POST'])
# def upload_image():
#     # 接收文件和算法选择
#     file = request.files['image']
#     algorithm_name = request.form.get('algorithm')
#
#     # 生成唯一任务ID
#     task_id = str(uuid.uuid4())
#
#     # 创建任务目录
#     task_input_dir = os.path.join(TASK_BASE_DIR, task_id, 'input')
#     task_output_dir = os.path.join(TASK_BASE_DIR, task_id, 'output')
#     os.makedirs(task_input_dir, exist_ok=True)
#     os.makedirs(task_output_dir, exist_ok=True)
#
#     # 保存上传文件
#     input_path = os.path.join(task_input_dir, 'input.jpg')
#     file.save(input_path)
#
#     # 存储任务信息到Redis
#     redis_key = f'task:{task_id}'
#     redis_client.hset(redis_key, 'status', 'pending')
#     redis_client.hset(redis_key, 'algorithm', algorithm_name)
#     redis_client.hset(redis_key, 'input_path', input_path)
#     redis_client.hset(redis_key, 'output_dir', task_output_dir)
#
#     # 将任务ID加入队列
#     redis_client.lpush('task_queue', task_id)
#
#     return jsonify({'task_id': task_id, 'status_url': f'/task/{task_id}'})
#
# @models_bp.route('/task/<task_id>', methods=['GET'])
# def get_task_status(task_id):
#     task_key = f'task:{task_id}'
#     if not redis_client.exists(task_key):
#         return jsonify({'error': '任务不存在'}), 404
#
#     status = redis_client.hget(task_key, 'status').decode()
#     response = {
#         'task_id': task_id,
#         'status': status,
#         'result_url': None
#     }
#
#     if status == 'completed':
#         result_path = redis_client.hget(task_key, 'result_path').decode()
#         response['result_url'] = f'/results/{task_id}'
#
#     elif status == 'failed':
#         response['error'] = redis_client.hget(task_key, 'error').decode()
#
#     return jsonify(response)
#
# @models_bp.route('/results/<task_id>', methods=['GET'])
# def get_result(task_id):
#     task_key = f'task:{task_id}'
#     result_path = redis_client.hget(task_key, 'result_path')
#     if not result_path:
#         return jsonify({'error': '结果不存在'}), 404
#     return send_file(result_path, mimetype='image/jpeg')
