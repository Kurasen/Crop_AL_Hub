import os
from werkzeug.utils import secure_filename

from app.core.exception import ValidationError

UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'test')
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
