from flask import Blueprint, request

user_bp = Blueprint('user', __name__, url_prefix='/api/v1/users')

#
# # Create 创建用户
# @user_bp.route('', methods=['POST'])
# def create_user():
#
#
# # Read 获取用户
# @user_bp.route('', methods=['GET'])
# def get_users():
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
