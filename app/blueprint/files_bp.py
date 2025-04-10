from flask import request, Blueprint, g

from app.config import FileConfig
from app.core.exception import FileUploadError, logger
from app.exts import db
from app.model.model_service import ModelService
from app.token.JWT import token_required, resource_owner
from app.user.user_service import UserService
from app.utils import create_json_response
from app.utils.file_process import FileUploader

files_bp = Blueprint('files', __name__, url_prefix='/api/v1/files')

# 假设已有的上传器类
uploader = FileUploader()


@files_bp.route('/upload/<string:upload_type>/<int:data_id>/<string:file_type>', methods=['POST'])
@resource_owner(
    resource_type_param='upload_type',
    id_param='data_id',
    inject_instance=False
)
def upload_file(upload_type, data_id, file_type):
    print(upload_type, data_id, file_type)
    # 验证上传类型是否存在
    config = FileConfig.UPLOAD_CONFIG.get(upload_type)
    if not config:
        return create_json_response({'error': {"message": "暂不支持其他选择"}}, 400)

    # 检查 file_type 是否在配置允许范围内
    if 'file_types' in config and file_type not in config['file_types']:
        allowed = ", ".join(config['file_types'])
        return create_json_response({'error': {"message": "不支持的类型"}}, 400)

    # 执行核心验证逻辑
    try:
        uploader.validate_uploaded_file(
            request.files,
            config["allowed_extensions"],
            config["max_size"],
            file_type=file_type
        )

        # 保存文件并返回结果
        saved_path = uploader.save_uploaded_file(
            request.files['file'],
            g.current_user.id,
            upload_type,
            file_type=file_type
        )
        print(f"saved_path: {saved_path}")

        # # 3. 如果上传类型是 model，更新对应模型的 icon 字段
        # #if upload_type == "model":
        #     # 获取模型实例
        #     model = ModelService.get_model_by_id(data_id)
        #
        #     # # 验证权限（确保当前用户是模型所有者）
        #     # if model.user_id != g.current_user.id:
        #     #     return create_json_response({"error": {"message": "无权操作"}}, 403)
        #
        #     # 更新 icon 字段并提交到数据库
        #     if file_type == "icon":
        #         model.icon = saved_path
        #         db.session.commit()
        #
        #     return create_json_response({
        #         "data": {
        #             "photo_url": {
        #                 "re_url": f"{saved_path}",
        #                 "ab_url": f"{FileConfig.FILE_BASE_URL}/{saved_path}"}
        #             }
        #     }, 201)

        # 数据库更新（仅允许 icon/avatars 类型）
        # 定义允许存数据库的 file_type 与模型映射关系
        database_mapping = {
            "model": {
                "icon": (ModelService.get_model_by_id, "icon")  # (模型查询方法, 字段名)
            },
            "user": {
                "avatars": (UserService.get_user_by_id, "avatar")
            }
        }

        if upload_type in database_mapping and file_type in database_mapping[upload_type]:
            # 获取模型和字段信息
            get_model_func, field_name = database_mapping[upload_type][file_type]
            model_instance = get_model_func(data_id)

            # 更新数据库字段
            setattr(model_instance, field_name, saved_path)
            db.session.commit()

        return create_json_response({
            "data": {
                "file_url": {
                    "relative_path": saved_path,
                    "absolute_url": f"{FileConfig.FILE_BASE_URL}/{saved_path}"
                },
                #"saved_to_database": upload_type in database_mapping and file_type in database_mapping[upload_type]
            }
        }, 201)

    except FileUploadError as e:
        logger.warning(f"文件验证失败: {str(e)}")
        return create_json_response({'error': {"message": f'{str(e)}'}}, 400)
    except Exception as e:
        logger.error(f"服务器异常: {str(e)}", exc_info=True)
        db.session.rollback()
        return create_json_response({'error': {"message": f'{str(e)}'}}, 500)
