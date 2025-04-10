from datetime import datetime

from flask import Blueprint, request, g

from app.application.app import App
from app.application.app_service import AppService
from app.exts import db
from app.schemas.app_schema import AppCreateSchema, AppUpdateSchema, AppSearchSchema
from app.token.JWT import token_required
from app.utils import create_json_response
from app.utils.file_process import allowed_file, save_uploaded_file, FileUploader

apps_bp = Blueprint('apps', __name__, url_prefix='/api/v1/apps')


@apps_bp.route('/<int:app_id>', methods=['GET'])
def get_app(app_id):
    """
    获取特定模型的详细信息
    """
    app = AppService.get_app_by_id(app_id)
    return create_json_response({
        "data": app.to_dict()
    })


@apps_bp.route('', methods=['GET'])
def search():
    """
    查询数据集，支持模糊查询和过滤条件。
    示例请求参数：
    ?name=
    """
    search_params = AppSearchSchema().load(request.args.to_dict())
    result = AppService.search_apps(search_params)
    return create_json_response(result)


@apps_bp.route('', methods=['POST'])
@token_required(admin_required=True)
def save_app():
    """
    创建新数据集
    """
    form_data = request.get_json()
    print(f"form_data: {form_data}")
    files = request.files.get("icon")
    print(f"files: {files}")
    saved_path = None  # 初始化文件路径
    # 如果有文件上传则处理
    if files and files.filename != '':
        # 文件类型验证
        if not allowed_file(files.filename):
            return create_json_response({"error": "仅支持JPG/PNG格式图片"}, 400)
        # 文件大小验证
        max_size = 100 * 1024 * 1024
        file_data = files.read()
        if len(file_data) > max_size:
            return create_json_response({"error": f"文件大小超过{max_size//1024//1024}MB限制"}, 400)

        # 保存文件
        files.seek(0)  # 重置文件指针
        saved_path = save_uploaded_file(files, g.current_user.id, "banners")
        # 合并数据（如果有上传文件）
    if saved_path:
        form_data['banner'] = saved_path
    else:
        # 可以设置默认图片或留空
        form_data['banner'] = ''
    app_instance = AppCreateSchema().load(
        form_data,
        session=db.session
    )
    app_instance.user_id = g.current_user.id  # 注入当前用户ID
    result, status = AppService.save_app(app_instance)
    return create_json_response(result, status)


@apps_bp.route('/<int:app_id>', methods=['PUT'])
@token_required(model=App, id_param='app_id')
def update_app(instance):
    """
    更新现有数据集
    """
    updates = AppUpdateSchema().load(
        request.get_json(),
        partial=True,  # 允许部分更新
        instance=instance,  # 绑定到现有实例
        session=db.session
    )
    updates.updated_at = datetime.utcnow()
    result, status = AppService.update_app(updates)
    return create_json_response({"message": "更新成功"}, status)


# 删除现有数据集
@apps_bp.route('/<int:app_id>', methods=['DELETE'])
@token_required(model=App, id_param='app_id')
def delete_app(instance):
    """
    删除现有数据集
    """
    result, status = AppService.delete_app(instance)
    return create_json_response(result, status)
