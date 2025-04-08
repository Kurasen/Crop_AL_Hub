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
                "url": {
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



# @files_bp.route('/upload/<string:upload_type>', methods=['POST'])
# @token_required()
# def upload_file(upload_type):
#     # 1. 验证上传类型是否存在
#     if upload_type not in UPLOAD_CONFIG:
#         return create_json_response({"error": f"Invalid upload type: {upload_type}"}, 400)
#
#     # 2. 获取上传配置
#     config = UPLOAD_CONFIG[upload_type]
#     allowed_extensions = config["allowed_extensions"]
#     max_size = config["max_size"]
#     subdirectory = config["subdirectory"]
#
#     # 获取动态参数（示例获取file_type）
#     file_type = request.form.get("file_type")
#     if upload_type == "model" and not file_type:
#         return create_json_response({"error": "缺少file_type参数"}, 400)
#
#     # 3. 校验文件是否存在
#     if 'file' not in request.files:
#         return create_json_response({"message": "未选择文件"}, 400)
#     file = request.files['file']
#
#     # 4. 校验文件名和扩展名
#     filename = secure_filename(file.filename)
#     if not filename:
#         return create_json_response({"message": "无效的文件名"}, 400)
#     ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
#     if ext not in allowed_extensions:
#         return create_json_response({"error": f"文件名无效 {ext} 不允许使用文件扩展名 {upload_type}"}, 400)
#
#     # 5. 校验文件大小
#     file_size = len(file.read())  # 注意：这里会消耗文件指针，需重置
#     file.seek(0)  # 重置指针到文件开头
#     if file_size > max_size:
#         return create_json_response({"error": f"File size exceeds {max_size // 1024 // 1024}MB limit"}), 400
#
#     # 6. 自定义保存逻辑（例如关联业务ID）
#     # 假设需要关联用户ID或模型ID，可通过请求参数传递
#     # business_id = request.form.get("business_id")  # 例如 user_id 或 model_id
#     # if not business_id:
#     #     return create_json_response({"error": "缺少business_id"}), 400
#
#     # 7. 保存文件到对应目录
#     saved_path = uploader.save_file(
#         uploaded_file=file,
#         user_id=g.current_user.id,
#         subdirectory=subdirectory.format(  # 关键：参数替换
#             user_id=g.current_user.id,
#             file_type=file_type  # 新增参数
#         )
#         # business_id=business_id
#     )
#     print(f"保存地址：{saved_path}")
#
#     # 8. 返回响应（可自定义返回字段）
#     return create_json_response({"message": "文件上传成功"}, 201)
