from flask import request, Blueprint, g
from app.config import Config
from app.core.exception import FileUploadError, logger
from app.exts import db
from app.model.model_service import ModelService
from app.token.JWT import token_required
from app.utils import create_json_response
from app.utils.file_process import FileUploader

files_bp = Blueprint('files', __name__, url_prefix='/api/v1/files')

# 假设已有的上传器类
uploader = FileUploader()


@files_bp.route('/upload/<string:upload_type>/<int:data_id>/<string:file_type>', methods=['POST'])
@token_required()
def upload_file(upload_type, data_id, file_type):
    print(upload_type, data_id, file_type)
    # 1. 验证上传类型是否存在
    global saved_path
    config = Config.UPLOAD_CONFIG.get(upload_type)
    if upload_type != "model":
        return create_json_response({'error': {"message": "暂不支持其他选择"}}, 400)

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

    # 3. 如果上传类型是 model，更新对应模型的 icon 字段
    #if upload_type == "model":
        # 获取模型实例
        model = ModelService.get_model_by_id(data_id)

        # # 验证权限（确保当前用户是模型所有者）
        # if model.user_id != g.current_user.id:
        #     return create_json_response({"error": {"message": "无权操作"}}, 403)

        # 更新 icon 字段并提交到数据库
        if file_type == "icon":
            model.icon = saved_path
            db.session.commit()

        return create_json_response({
            "data": {
                "photo_url": {
                    "re_url": f"{saved_path}",
                    "ab_url": f"http://10.0.4.71:8080/file/{saved_path}"}
                }
        }, 201)

    except FileUploadError as e:
        logger.warning(f"文件验证失败: {str(e)}")
        return create_json_response({'error': {"message": f'{str(e)}'}}, 400)
    except Exception as e:
        logger.error(f"服务器异常: {str(e)}", exc_info=True)
        db.session.rollback()
        return create_json_response({'error': {"message": '服务器异常，文件上传失败'}}, 500)

