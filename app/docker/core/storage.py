from pathlib import Path
from app.config import Config
import os
import shutil
from app.core.exception import logger, ImageProcessingError, NotFoundError, ValidationError
from pathlib import Path
from PIL import Image, UnidentifiedImageError

from app.docker.core.celery_app import CeleryManager


class FileStorage:
    @staticmethod
    def is_file_corrupted(file_path):
        """
        检查文件是否损坏。
        :param file_path: 文件路径
        :return: True（损坏）或 False（正常）
        """
        file_path = Path(file_path)

        # 增加路径类型校验
        if not file_path.is_file():  # 确保是文件而非目录
            raise ValidationError("非文件")

        # 原有逻辑保持不变
        if not file_path.exists():
            raise NotFoundError("未找到文件")

        # 仅对图片文件进行损坏检测
        if file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
            try:
                with Image.open(file_path) as img:
                    img.verify()  # 验证文件是否完整
            except (UnidentifiedImageError, IOError) as e:
                raise ImageProcessingError(f"文件已经损坏") from e
            except Exception as e:
                raise ImageProcessingError(f"文件检测失败") from e

    @staticmethod
    def validate_directory(directory):
        """检查目录是否存在且非空"""
        dir_path = Path(directory)
        if not dir_path.is_dir():
            raise ValueError(f"目录不存在: {directory}")
        if not any(dir_path.iterdir()):
            raise RuntimeError(f"目录为空: {directory}")
        return dir_path

    @staticmethod
    def save_upload(file_stream, save_dir, file_name):
        """文件保存方法"""
        # 重置文件指针到起始位置
        if hasattr(file_stream, "seekable") and file_stream.seekable():
            file_stream.seek(0)
        # 确保父目录存在
        save_dir = Path(save_dir)
        save_dir.parent.mkdir(parents=True, exist_ok=True)

        save_path = save_dir / file_name

        # 使用二进制追加模式写入（确保原子性）
        try:
            with open(save_path, 'wb') as f:
                while True:
                    chunk = file_stream.read(4096)
                    if not chunk:
                        break
                    f.write(chunk)
                f.flush()
                os.fsync(f.fileno())
        except IOError as e:
            logger.error(f"文件写入失败: {save_path} - {str(e)}")
            raise

        # 验证文件大小
        if save_path.stat().st_size == 0:
            os.remove(save_path)
            raise ValueError("保存文件为空")

        # 延迟检测（解决文件系统同步问题）
        from time import sleep
        sleep(0.1)  # 根据实际需要调整

        # 二次验证损坏
        if FileStorage.is_file_corrupted(save_path):
            os.remove(save_path)
            raise ValueError(f"文件损坏，已被删除")

        return str(save_dir)

    @staticmethod
    def get_result_path(task_id):
        """获取输出文件路径"""
        result_dir = Path(Config.OUTPUT_FOLDER) / f"task_{task_id}"
        if not result_dir.exists():
            raise FileNotFoundError("结果目录不存在")
        return str(result_dir)

    @staticmethod
    def generate_upload_path(image_name, task_id):
        """生成符合Docker规范的宿主机路径"""
        input_subdir = f"task_{task_id}"
        host_upload_dir = Path(Config.UPLOAD_FOLDER) / image_name / input_subdir
        host_upload_dir.mkdir(parents=True, exist_ok=True)
        return host_upload_dir

    @staticmethod
    def upload_input(file, image_name, task_id):
        """保存上传的文件并返回文件路径"""
        # 生成保存路径
        upload_dir = FileStorage.generate_upload_path(image_name, task_id)

        # 获取原始文件名并处理后缀
        original_filename = file.filename
        file_ext = Path(original_filename).suffix # 强制转为大写

        # # 允许的后缀列表（根据需求调整）
        # allowed_extensions = {'.JPG', '.JPEG', '.PNG'}
        #
        # # 验证文件格式
        # if file_ext not in allowed_extensions:
        #     raise ValidationError(f"不支持的文件格式: {file_ext}，仅支持 {allowed_extensions}")
        #
        # # 构建新文件名（固定为001 + 原后缀）
        new_filename = f"001{file_ext}"

        FileStorage.save_upload(
            file_stream=file,
            save_dir=upload_dir,  # 目录路径
            file_name=new_filename
        )
        return str(upload_dir)  # 返回目录路径，而非文件路径

    # @staticmethod
    # def clean_directory(directory, logger):
    #     """清理目录"""
    #     dir_path = Path(directory)
    #     if dir_path.exists():
    #         try:
    #             shutil.rmtree(dir_path)
    #             logger.info(f"清理目录成功: {dir_path}")
    #         except Exception as e:
    #             logger.error(f"清理目录失败: {dir_path} - {str(e)}")


# 单例实例
storage = FileStorage()


@CeleryManager.get_celery().task
def cleanup_directory(input_dir, output_dir):
    try:
        # 清理输入目录
        input_path = Path(input_dir)
        if input_path.exists():
            shutil.rmtree(input_path)
            logger.info(f"清理输入目录成功: {input_dir}")
        else:
            logger.warning(f"输入目录不存在，可能已被删除: {input_dir}")

        # 清理输出目录
        output_path = Path(output_dir)
        if output_path.exists():
            shutil.rmtree(output_path)
            logger.info(f"清理输出目录成功: {output_dir}")
        else:
            logger.warning(f"输出目录不存在，可能已被删除: {output_dir}")
    except Exception as e:
        logger.error(f"清理目录失败: {str(e)}", exc_info=True)