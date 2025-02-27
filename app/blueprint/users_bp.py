from flask import Blueprint, request

from app.schemas.users_shema import UserSearchSchema
from app.user.user_service import UserService
from app.utils import create_json_response

user_bp = Blueprint('user', __name__, url_prefix='/api/v1/users')


# Read 获取用户
@user_bp.route('/search', methods=['GET'])
def search():
    # data = UserSearchSchema().load(request.args.to_dict())
    data = request.get_json()
    result = UserService.search_users(data)
    return create_json_response(result)
#
#
# @user_bp.route('/<int:user_id>', methods=['GET'])
# def get_user(user_id):
#
#
# # Update 更新用户（全量替换）
# @user_bp.route('/<int:user_id>', methods=['PUT'])
# def update_user(user_id):
#
#
# # Delete 删除用户
# @user_bp.route('/<int:user_id>', methods=['DELETE'])
# def delete_user(user_id):
