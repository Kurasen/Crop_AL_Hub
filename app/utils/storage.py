from app.config import Config
import os

from app.core.exception import logger, ImageProcessingError, NotFoundError, ValidationError, FileSaveError, \
    FileValidationError
from pathlib import Path
from PIL import Image, UnidentifiedImageError


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
                raise ImageProcessingError("文件已经损坏") from e
            except Exception as e:
                raise ImageProcessingError("文件检测失败") from e

    @staticmethod
    def validate_directory(directory):
        """检查目录是否存在且非空"""
        dir_path = Path(directory)
        if not dir_path.is_dir():
            raise FileValidationError(f"目录不存在: {directory}")
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
        save_dir.mkdir(parents=True, exist_ok=True)  # ✅ 直接创建完整目录

        save_path = save_dir / file_name

        print(f"保存目录：{save_dir.absolute()}")  # 输出：/home/zhaohonglong/.../temp/models/readme
        print(f"目录是否存在：{save_dir.exists()}")  # 输出：True

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
            raise FileSaveError("保存文件为空")

        # 延迟检测（解决文件系统同步问题）
        from time import sleep
        sleep(0.1)  # 根据实际需要调整

        # 二次验证损坏
        if FileStorage.is_file_corrupted(save_path):
            os.remove(save_path)
            raise ValueError("文件损坏，已被删除")

        return str(save_dir)

    @staticmethod
    def get_result_path(task_id):
        """获取输出文件路径"""
        result_dir = Path(Config.OUTPUT_FOLDER) / f"task_{task_id}"
        if not result_dir.exists():
            raise NotFoundError("结果丢失")
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

        # 获取文件后缀并转为小写
        original_filename = file.filename
        file_ext = Path(original_filename).suffix  # 提取后缀并标准化

        # 允许的后缀列表（根据需求调整）
        allowed_extensions = {'.bmp', '.dib', '.png', '.jpg', '.jpeg', '.pbm', '.pgm', '.ppm', '.tif', '.tiff', '.JPG'}

        # 验证文件格式
        if file_ext not in allowed_extensions:
            raise FileValidationError("文件类型不被支持")

        # 构建新文件名（固定为001 + 原后缀）
        new_filename = f"001{file_ext}"

        FileStorage.save_upload(
            file_stream=file,
            save_dir=upload_dir,  # 目录路径
            file_name=new_filename
        )
        return str(upload_dir)  # 返回目录路径，而非文件路径


# 单例实例
storage = FileStorage()
