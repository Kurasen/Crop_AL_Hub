# import time
# from pathlib import Path
#
# from flask import Flask, request, jsonify, Blueprint, current_app
# from celery import Celery
# import docker
# import uuid
# from docker.errors import NotFound, APIError
# import logging
# import os
#
#
# test_bp = Blueprint('test', __name__, url_prefix='/api/v1/test')
#
# # 确保 Celery 初始化正确
# celery = Celery(__name__, broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')
# celery.conf.update(
#     task_default_queue='default',  # 明确默认队列
#     broker_connection_retry_on_startup=True,
#     task_routes={
#         'test_app.run_algorithm': {'queue': 'default'}  # 修正模块名为实际模块名（如 app）
#     },
#     worker_concurrency=1,  # 限制并发度为 1
#     worker_pool='solo'  # 使用 solo 模式（适用于 Windows）
# )
#
# # 初始化Docker客户端
# docker_client = docker.DockerClient(base_url='tcp://127.0.0.1:2375')
#
#
# # 文件存储路径配置
# UPLOAD_FOLDER = Path(r'D:\Technology\Code\Python\Crop_AL_Hub\app\docker\data\images').resolve()  # 使用 Path 对象
# OUTPUT_FOLDER = Path(r'D:\Technology\Code\Python\Crop_AL_Hub\app\docker\output').resolve()  # 使用 Path 对象
#
# # 确保目录存在
# UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
# OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
#
#
# # Celery任务：运行Docker容器
# @celery.task(bind=True, name='test_app.run_algorithm')
# def run_algorithm(self, input_path, task_id):
#     try:
#
#         current_app.logger.info(f"\n=== 任务启动 [{task_id}] ===")
#
#         # 宿主机输入目录（原生 Windows 路径）
#         host_input_dir = Path(input_path)
#         current_app.logger.info(f"宿主机输入目录验证 → {host_input_dir} (存在: {host_input_dir.exists()})")
#
#         # 宿主机输出目录（原生 Windows 路径）
#         host_output_dir = OUTPUT_FOLDER / f"task_{task_id}"
#         host_output_dir.mkdir(parents=True, exist_ok=True)
#
#         # 启动容器，挂载输入和输出目录
#         container = docker_client.containers.run(
#             "test-fake-algorithm",
#             volumes={
#                 str(host_input_dir): {'bind': '/data/images', 'mode': 'ro'},
#                 str(host_output_dir): {'bind': '/output', 'mode': 'rw'}
#             },
#             detach=True,
#             auto_remove=True
#         )
#
#         # 获取完整容器日志
#         logs = container.logs().decode('utf-8')
#         current_app.logger.info(f"容器日志:\n{logs}")
#
#
#         # 等待容器退出
#         exit_status = container.wait()['StatusCode']
#         current_app.logger.info(f"容器退出状态码: {exit_status}")
#
#         # 检查输出目录（添加详细文件列表输出）
#         output_files = list(host_output_dir.glob('*'))
#         current_app.logger.info(f"输出目录内容: {[f.name for f in output_files]}")
#         if not output_files:
#             raise FileNotFoundError(f"输出目录为空: {host_output_dir}")
#
#         return {'status': 'success', 'output': str(host_output_dir)}
#     except Exception as e:
#         current_app.logger.error(f"任务失败详情: {str(e)}")
#         return {'status': 'error', 'message': str(e)}
#
#
# # Flask路由：上传文件并触发任务
# @test_bp.route('/process', methods=['POST'])
# def process_image():
#     if 'file' not in request.files:
#         return jsonify({'error': '未上传文件d'}), 400
#
#     file = request.files['file']
#
#     # 生成符合Docker规范的宿主机路径
#     task_id = str(uuid.uuid4())
#     input_subdir = f"task_{task_id}"
#
#     # 使用绝对路径（关键修改）
#     host_upload_dir = Path(UPLOAD_FOLDER) / input_subdir
#     host_upload_dir.mkdir(parents=True, exist_ok=True)
#
#     # 保存文件
#     file_path = host_upload_dir / file.filename
#     file.save(file_path)
#     current_app.logger.info(f"文件保存位置: {file_path}")
#
#     # 提交任务时传递绝对路径
#     task = run_algorithm.delay(str(host_upload_dir), task_id)  # 确保传递绝对路径
#
#     return jsonify({'task_id': task.id}), 202
#
#
# # Flask路由：查询任务状态
# @test_bp.route('/task/<task_id>', methods=['GET'])
# def get_task_status(task_id):
#     task = run_algorithm.AsyncResult(task_id)
#     if task.state == 'PENDING':
#         response = {'status': 'pending'}
#     elif task.state == 'SUCCESS':
#         response = {'status': 'success', 'result': task.result}
#     elif task.state == 'FAILURE':
#         response = {'status': 'error', 'message': str(task.info)}
#     else:
#         response = {'status': task.state}
#     return jsonify(response), 200
#
#
