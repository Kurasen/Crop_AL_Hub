import os
from pathlib import Path

from app.config import Config
from app.core.exception import logger, ImageProcessingError

from app.docker.core.celery_app import CeleryManager

from app.docker.core.docker_clinet import docker_client
from app.utils.storage import FileStorage
from app.utils.file_process import classify_files

# 文件存储路径配置
UPLOAD_FOLDER = Config.UPLOAD_FOLDER
OUTPUT_FOLDER = Config.OUTPUT_FOLDER

# 确保目录存在
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)


@CeleryManager.get_celery().task(bind=True,  expires=86400)
def run_algorithm(self, input_path, task_id, image_name, instruction=None):
    try:
        logger.info(f"\n=== 任务启动 [{task_id}] ===")

        # 宿主机输入目录
        host_input_dir = Path(input_path)

        # 检查该目录下是否有文件
        files_in_directory = list(host_input_dir.glob('*'))  # 使用 * 匹配所有文件
        if not files_in_directory:
            print(files_in_directory)
            raise RuntimeError("文件不存在")

        # 检查文件是否损坏
        for file_path in files_in_directory:
            FileStorage.is_file_corrupted(file_path)

        # 检查目录权限
        os.chmod(host_input_dir, 0o777)  # 任务开始前设置权限
        logger.info(f"输入目录权限: {oct(host_input_dir.stat().st_mode)}")

        # 宿主机输出目录
        host_output_dir = OUTPUT_FOLDER / image_name / f"task_{task_id}"
        host_output_dir.mkdir(parents=True, exist_ok=True)

        # # 构建容器命令
        # docker_command = ["python3", "main.py", "-i", "/data", "-o", "/result"]
        # if instruction:
        #     docker_command.extend(instruction.split())

        docker_command = instruction

        container_info = docker_client.run_algorithm_container(
            image_name=image_name,
            host_input_dir=host_input_dir,
            host_output_dir=host_output_dir,
            command=docker_command
        )

        # 验证输出结果
        output_files = list(host_output_dir.glob('*'))
        logger.info("输出目录内容: %s", [f.name for f in output_files])
        if not output_files:
            raise RuntimeError("算法未生成任何输出文件")

        processed_files = classify_files(output_files, image_name, task_id)
        return {
            'status': 'SUCCESS',
            'processed_files': processed_files
        }

    except Exception as e:
        logger.error(f"任务失败详情: {str(e)}", exc_info=True)
        # 如果是文件损坏或特定异常，直接标记任务失败，不进行重试
        if isinstance(e, (ImageProcessingError, RuntimeError)):
            self.update_state(
                state='FAILURE',
                meta={
                    'exc_type': type(e).__name__,  # 异常类型
                    'exc_message': str(e)  # 异常消息
                }
            )
            raise

        # 其他异常触发有限次重试
        retry_count = self.request.retries
        if retry_count < 2:  # 最多重试2次
            logger.warning(f"任务重试中，重试次数: {retry_count + 1}")
            raise self.retry(exc=e, countdown=2 ** retry_count)
        else:
            self.update_state(
                state='FAILURE',
                meta={
                    'exc_type': type(e).__name__,  # 异常类型
                    'exc_message': f'重试耗尽: {str(e)}'  # 异常消息
                }
            )
            raise

    finally:
        logger.info(f"任务结束 [{task_id}]")


from app.docker.core.redis_task import RedisTaskQueue


# 任务执行端 (独立服务)
class TaskExecutor:
    def __init__(self):
        self.task_queue = RedisTaskQueue(queue_name='image_tasks')

    def run_forever(self):
        while True:
            task = self.task_queue.pop_task()
            if task:
                try:
                    self.task_queue.update_status(task['task_id'], "running")
                    # 执行容器操作...
                    self.task_queue.update_status(task['task_id'], "completed")
                except Exception as e:
                    self.task_queue.update_status(task['task_id'], "failed", {"error": str(e)})
