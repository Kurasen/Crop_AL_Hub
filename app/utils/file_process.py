import time
import uuid

from werkzeug.utils import secure_filename

from app.config import Config
from app.core.exception import ValidationError, logger, FileUploadError
from pathlib import Path


class FileUploader:
    def __init__(self):
        self.base_folder = Path(Config.USER_FOLDER)

    def validate_uploaded_file(self, files, allowed_ext, max_size, file_type=None):
        """统一文件验证入口"""
        if 'file' not in files:
            raise FileUploadError("未选择文件")

        file = files['file']
        filename = file.filename
        if not filename:
            raise FileUploadError("无效文件名")
        # 打印原始文件名用于调试
        print(f"原始文件名: {repr(filename)}")

        # 打印文件名用于调试
        print(repr(filename))

        # 手动处理扩展名，防止提取后缀时出错
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        print(f"ext:{ext}")

        if ext not in allowed_ext:
            print(allowed_ext)
            raise FileUploadError("文件类型不支持")

        if len(file.read()) > max_size:
            raise FileUploadError("文件大小超出限制")
        file.seek(0)  # 重置文件指针

    def save_uploaded_file(self, uploaded_file, user_id, upload_type, file_type=None):
        """统一文件保存入口"""
        config = Config.UPLOAD_CONFIG[upload_type]
        subdirectory = config['subdirectory'].format(
            user_id=user_id,
            file_type=file_type
        )

        # 安全文件名生成
        safe_name = self.generate_safe_filename(uploaded_file.filename)
        save_path = self.base_folder / str(user_id) / subdirectory
        save_path.mkdir(parents=True, exist_ok=True)

        uploaded_file.save(str(save_path / safe_name))
        return f"user/{user_id}/{subdirectory}/{safe_name}"

    @staticmethod
    def generate_safe_filename(filename):
        """生成唯一安全文件名"""
        name, ext = Path(filename).stem, Path(filename).suffix
        return f"{uuid.uuid4()}_{int(time.time())}{ext}"


#
# class FileUploader:
#     def __init__(self, base_folder=None):
#         self.base_folder = Path(base_folder or Config.USER_FOLDER)
#         self.allowed_extensions = set()
#
#     def set_allowed_extensions(self, extensions):
#         """允许动态设置允许的文件类型"""
#         self.allowed_extensions = set(ext.lower() for ext in extensions)
#
#     def allowed_file(self, filename):
#         """检查文件扩展名合法性"""
#         return '.' in filename and \
#             filename.rsplit('.', 1)[1].lower() in self.allowed_extensions
#
#     def generate_safe_filename(self, original_filename):
#         """生成安全且唯一的文件名"""
#         # 获取文件扩展名
#         ext = Path(original_filename).suffix.lower()
#         # 使用UUID+时间戳保证唯一性
#         unique_str = f"{uuid.uuid4().hex}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
#         return f"{unique_str}{ext}"
#
#     def save_file(self, uploaded_file, user_id, subdirectory="upload"):
#         """
#         通用文件保存方法
#         :param uploaded_file: Werkzeug FileStorage对象
#         :param user_id: 用户ID
#         :param subdirectory: 自定义子目录（默认存放在 user_id/uploads）
#         :return: 文件相对路径
#         """
#         try:
#             # 构建安全目录路径
#             user_dir = self.base_folder / str(user_id) / subdirectory
#             user_dir.mkdir(parents=True, exist_ok=True)
#
#             # 处理文件名
#             original_filename = secure_filename(uploaded_file.filename)
#             safe_filename = self.generate_safe_filename(original_filename)
#
#             # 保存文件
#             file_path = user_dir / safe_filename
#             uploaded_file.save(str(file_path))
#
#             # 返回相对路径（根据实际需求调整）
#             return f"{user_id}/{subdirectory}/{safe_filename}"
#
#         except Exception as e:
#             logger.error(f"文件上传失败: {str(e)}")
#             raise


USER_FOLDER = Config.USER_FOLDER
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}


# 检查文件扩展名是否有效
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(uploaded_file, user_id: int, name: str):
    if not allowed_file(uploaded_file.filename):
        raise ValidationError("不支持的文件类型")

    # 创建用户专属目录 user_folder/user_id/name
    user_dir = USER_FOLDER / str(user_id) / secure_filename(name)
    user_dir.mkdir(parents=True, exist_ok=True)

    # 生成安全文件名
    original_filename = secure_filename(uploaded_file.filename)
    filename = f"{int(time.time())}_{original_filename}"  # 添加时间戳防重名
    file_path = user_dir / filename

    uploaded_file.save(str(file_path))

    return file_path


def classify_files(file_list, image_name, task_id):
    """文件分类处理"""
    image_types = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
    results = {
        'images': [],  # 存储Base64编码的图片
        'downloads': []  # 存储可下载文件链接
    }

    for file_path in file_list:
        file_name = file_path.name
        ext = Path(file_path).suffix.lower()
        # 统一生成访问URL
        file_url = f"http://10.0.4.71:8080/file/output/{image_name}/task_{task_id}/{file_name}"

        if ext in image_types:
            results['images'].append({
                'filename': file_name,
                'url': file_url  # 图片直接返回访问URL
            })
        else:
            # 生成下载链接（需要配合下载路由）
            results['downloads'].append({
                'filename': file_path.name,
                'url': file_url
            })
    return results
