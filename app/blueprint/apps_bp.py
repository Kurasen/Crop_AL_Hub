from datetime import datetime

from flask import Blueprint, request, g

from app.application.app import App
from app.application.app_service import AppService
from app.exts import db
from app.schemas.app_schema import AppCreateSchema, AppUpdateSchema, AppSearchSchema
from app.token.JWT import resource_owner, admin_required
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
    print(f"search_params: {search_params}")
    result = AppService.search_apps(search_params)
    return create_json_response(result)


@apps_bp.route('', methods=['POST'])
@admin_required
def save_app():
    """
    创建新数据集
    """
    request_data = request.get_json()
    request_data['user_id'] = g.current_user.id
    app_instance = AppCreateSchema().load(request_data, session=db.session)
    result, status = AppService.create_app(app_instance)
    return create_json_response(result, status)


@apps_bp.route('/<int:app_id>', methods=['PUT'])
@resource_owner(model=App, id_param='app_id')
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
@resource_owner(model=App, id_param='app_id')
def delete_app(instance):
    """
    删除现有数据集
    """
    result, status = AppService.delete_app(instance)
    return create_json_response(result, status)
