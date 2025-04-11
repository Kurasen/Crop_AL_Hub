import os
import re
from typing import Optional

from app.config import FileConfig
from app.core.exception import NotFoundError, ValidationError


class ImageURLHandlerUtils:

    @staticmethod
    def validate_url_format(url: str):
        """验证URL是否符合服务器规范"""
        expected_prefix = FileConfig.FILE_BASE_URL
        if not url.startswith(expected_prefix):
            raise ValidationError("仅支持访问本机服务器文件资源")
        return True

    @staticmethod
    def extract_relative_path(url: str) -> str:
        """从URL中提取相对路径（去掉前缀）"""
        # 假设已经通过validate_url_format验证
        return url[len(FileConfig.FILE_BASE_URL):].lstrip('/')

    @staticmethod
    def build_local_path(relative_path: str) -> str:
        """将相对路径拼接为本地完整路径"""
        base_path = FileConfig.LOCAL_FILE_BASE
        full_path = os.path.abspath(os.path.join(base_path, relative_path))

        # 防止路径遍历攻击
        if not full_path.startswith(os.path.abspath(base_path)):
            raise SecurityError("非法路径访问")
        return full_path

    @staticmethod
    def build_full_url(relative_path: Optional[str]) -> Optional[str]:
        """将相对路径拼接为完整URL（支持空值）"""
        if not relative_path:  # 处理 None 或空字符串
            return None
        base_url = FileConfig.FILE_BASE_URL
        return base_url + relative_path.lstrip('/')

    @classmethod
    def validate_photo_file(cls, url: str) -> str:
        """完整验证流程（组合方法）"""
        # 验证URL格式
        cls.validate_url_format(url)

        # 获取相对路径
        relative_path = cls.extract_relative_path(url)

        # 构建本地路径
        local_path = cls.build_local_path(relative_path)

        # 验证图片格式
        if not re.search(r"\.(jpg|jpeg|png)$", local_path, re.IGNORECASE):
            raise ValidationError("仅支持jpg/jpeg/png格式图片")

        # 验证文件存在性
        if not os.path.isfile(local_path):
            raise NotFoundError("图片无法找到或不存在")

        return relative_path  # 返回标准化相对路径(无前缀)


# 自定义异常类
class SecurityError(Exception):
    """路径安全异常"""
    pass
