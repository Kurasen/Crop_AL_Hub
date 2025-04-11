import os
import sys
import uuid
from pathlib import Path

import docker
from app.config import Config
from docker.errors import ImageNotFound

from app.core.exception import logger, ServiceException


class DockerManager:
    def __init__(self):
        #根据操作系统类型设置不同的Docker连接地址
        if sys.platform == 'linux':
            # Linux系统使用服务器地址
            self.client = docker.DockerClient(base_url='tcp://127.0.0.1:2375')
            logger.info("Docker进程已经启动")
        else:
            # Windows/Mac系统自动检测本地Docker
            self.client = None
            logger.info("Docker进程未启动")

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
        global container
        try:
            # 创建输出目录（如果不存在）
            Path(host_output_dir).mkdir(parents=True, exist_ok=True)
            logger.info("输入目录文件列表: %s", os.listdir(host_input_dir))

            # 配置容器卷映射
            volumes = {
                str(host_input_dir): {'bind': '/data', 'mode': 'rw'},
                str(host_output_dir): {'bind': '/result', 'mode': 'rw'}
            }

            # 启动容器
            container = self.client.containers.run(
                image_name,
                name=f"{image_name}_{uuid.uuid4()}",  # 保证容器名称唯一
                command=command,
                volumes=volumes,
                environment={
                    "TZ": Config.timezone,
                    "LANG": "C.UTF-8",  # 强制容器使用UTF-8
                    "LC_ALL": "C.UTF-8"
                },
                detach=True,
                auto_remove=False,  # 关闭自动删除
                remove=False,  # 防止自动清理
                user='root',
                privileged=True,
                stdout=True,  # 确保捕获标准输出
                stderr=True  # 确保捕获错误输出
            )

            # 同步获取日志
            logs = []
            exit_code = 1  # 默认错误状态
            try:
                # 合并日志流处理和等待退出
                for line in container.logs(stream=True, follow=True):
                    log_entry = line.decode().strip()
                    logs.append(log_entry)
                    logger.info("[容器日志] %s", log_entry)

                # 获取退出状态（此时容器已停止）
                exit_status = container.wait()
                exit_code = exit_status['StatusCode']
            except docker.errors.NotFound as e:
                logger.warning("容器日志流中断: %s", str(e))
            except docker.errors.APIError as e:
                if "marked for removal" not in str(e):
                    raise ServiceException(f"日志流异常: {str(e)}")

            return {
                "exit_code": exit_code,
                "host_output_dir": host_output_dir,
                "logs": "\n".join(logs)
            }

        except docker.errors.DockerException as e:
            error_type = "容器操作失败"
            # 细化错误类型判断
            if "No such image" in str(e):
                error_type = "镜像不存在"
            elif "port is already allocated" in str(e):
                error_type = "端口冲突"
            logger.error("%s: %s", error_type, str(e))
            raise ServiceException(f"{error_type}: {str(e)}")
        except Exception as e:
            logger.error("未知错误: %s", str(e), exc_info=True)
            raise ServiceException("系统内部错误")

        finally:
            # 确保清理容器
            if container:
                try:
                    container.remove(force=True)
                    logger.info("容器清理完成")
                except docker.errors.NotFound:
                    pass
                except Exception as e:
                    logger.warning("容器清理异常: %s", str(e))


# 单例模式初始化
docker_client = DockerManager()
