import logging
import os
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from app.config import FileConfig
from app.core.exception import NotFoundError, ValidationError, SecurityError


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
        return f"{base_url}/{relative_path.lstrip('/')}"

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
            raise NotFoundError("图片已失效")

        return relative_path  # 返回标准化相对路径(无前缀)


    @staticmethod
    def parse_temp_url_components(url: str) -> dict:
        """严格基于 TEMP_BASE_URL 解析URL参数"""
        try:
            # 获取标准化路径（兼容URL编码和不同系统路径分隔符）
            parsed = urlparse(url)
            logging.info(f"URL解析结果: {parsed}")

            # 标准化路径（统一小写并去除首尾斜杠）
            normalized_path = parsed.path.strip("/").lower()
            file_base_path = urlparse(FileConfig.FILE_BASE_URL).path.strip("/").lower()

            # 验证FILE_BASE_URL路径部分
            if not normalized_path.startswith(file_base_path):
                raise ValidationError(f"URL路径必须包含基础前缀 {FileConfig.FILE_BASE_URL}")

            # 提取核心路径（去除FILE_BASE_URL部分）
            core_path = normalized_path[len(file_base_path):].strip("/")
            logging.info(f"核心路径: {core_path}")

            # 验证TEMP_BASE_URL结构
            temp_base = FileConfig.TEMP_BASE_URL.strip("/")
            if not core_path.startswith(temp_base):
                raise ValidationError(f"路径必须包含临时目录前缀 {temp_base}")

            # 分割路径参数
            parts = core_path.split("/")
            logging.debug(f"分割路径参数: {parts}")

            # 参数提取（路径结构: storage/temp/<user_id>/<upload_type>/<data_id>/<file_type>/<version>/<file_hash>）
            if len(parts) < 5:
                raise ValidationError("路径层级不足，需要至少5级结构")

            return {
                "user_id": int(parts[2]),       #18
                "upload_type": parts[3],        # model
                "data_id": int(parts[4]),        # 76
                "file_type": parts[5],           # readme
                "version": parts[6],             # 时间戳
                "file_hash": Path(parts[7]).stem # 2dd6b8e655b6ee32fddacd63b997
            }

        except ValidationError as e:
            logging.error(f"参数类型错误: {str(e)}")
            raise ValidationError("URL路径解析不符合规范")
        except Exception as e:
            logging.error(f"未知解析错误: {str(e)}")
            raise e

    @classmethod
    def validate_temp_url_format(cls, url: str) -> bool:
        """复合验证流程"""
        # 验证是否包含基础路径
        if FileConfig.TEMP_BASE_URL not in url:
            raise ValidationError(f"URL必须包含 {FileConfig.TEMP_BASE_URL} 路径")

        # 执行深度解析
        cls.parse_temp_url_components(url)
        return True

    @staticmethod
    def build_temp_redis_key(components: dict) -> str:
        """构建Redis键"""
        return f"temp:{components['user_id']}:{components['upload_type']}:{components['data_id']}:{components['file_type']}:{components['version']}:{components['file_hash']}"

