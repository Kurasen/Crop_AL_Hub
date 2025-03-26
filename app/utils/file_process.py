import os
from werkzeug.utils import secure_filename

from app.core.exception import ValidationError
from pathlib import Path
import base64

UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), '../../test')
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}


# 检查文件扩展名是否有效
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(uploaded_file):
    if not allowed_file(uploaded_file.filename):
        raise ValidationError("不支持的文件类型")

    # 创建目录（线程安全方式）
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    filename = secure_filename(uploaded_file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)

    uploaded_file.save(file_path)

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
        file_url = f"http://10.0.4.71:8080/file/{image_name}/task_{task_id}/{file_name}"

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
