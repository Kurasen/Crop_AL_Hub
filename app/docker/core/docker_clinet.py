import uuid
from pathlib import Path

import docker
from app.config import Config
from docker.errors import ImageNotFound

from app.core.exception import logger, ServiceException


class DockerManager:
    def __init__(self):
        self.client = docker.DockerClient(base_url='tcp://127.0.0.1:2375')

    @staticmethod
    def validate_image(image_name):
        try:
            docker_client.client.images.get(image_name)
        except docker.errors.ImageNotFound:
            raise ServiceException(f'镜像 {image_name} 未找到，请先拉取镜像')
        except docker.errors.APIError as e:
            logger.error(f"Docker服务异常: {str(e)}")
            raise ServiceException('Docker服务不可用')

    def run_algorithm_container(self, image_name, host_input_dir, host_output_dir, command):
        """运行算法容器并实时获取日志"""
        try:
            # 创建输出目录（如果不存在）
            Path(host_output_dir).mkdir(parents=True, exist_ok=True)

            # 配置容器卷映射
            volumes = {
                str(host_input_dir): {'bind': '/data', 'mode': 'ro'},
                str(host_output_dir): {'bind': '/result', 'mode': 'rw'}
            }

            # 启动容器
            container = self.client.containers.run(
                image_name,
                name=f"{image_name}_{uuid.uuid4()}",  # 保证容器名称唯一
                command=command,
                volumes=volumes,
                environment={"TZ": Config.timezone},
                detach=True,
                auto_remove=True,
                user='root',
                privileged=True
            )

            # 实时获取日志（通过生成器实现）
            def log_generator():
                for line in container.logs(stream=True):
                    yield line.decode().strip()

            return {
                "container": container,
                "log_generator": log_generator(),
                "host_output_dir": host_output_dir
            }

        except docker.errors.DockerException as e:
            logger.error(f"容器启动失败: {str(e)}")
            raise ServiceException(f"容器启动失败: {str(e)}")
        except Exception as e:
            logger.error(f"未知Docker错误: {str(e)}")
            raise ServiceException("Docker操作异常")

    def get_exit_status(self, container):
        """获取容器退出状态码"""
        try:
            return container.wait()['StatusCode']
        except docker.errors.NotFound:
            logger.warning("容器已自动移除")
            return -1


# 单例模式初始化
docker_client = DockerManager()
