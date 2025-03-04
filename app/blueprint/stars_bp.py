from flask import Blueprint, request

from app.schemas.star_schema import StarCreateSchema
from app.star.star import StarType
from app.star.star_service import StarService
from app.token.JWT import token_required
from app.utils import create_json_response

stars_bp = Blueprint('stars', __name__, url_prefix='/api/v1/stars')


@stars_bp.route('/<int:target_id>/<string:star_type>', methods=['POST', 'DELETE'])
@token_required
def create_star(current_user, target_id, star_type):
    data = {'target_id': target_id, 'star_type': star_type, 'user_id': current_user["user_id"]}
    validated_data = StarCreateSchema().load(data)
    if request.method == 'POST':
        """添加收藏"""
        result, status = StarService.add_star(validated_data)
        return create_json_response(result, status)
    elif request.method == 'DELETE':
        """删除收藏"""
        result, status = StarService.remove_star(validated_data)
        return create_json_response(result, status)


@stars_bp.route('/count/<int:target_id>/<string:star_type>', methods=['GET'])
def get_star_count(target_id, star_type):
    """获取指定目标的收藏总数"""
    count = StarService.get_star_count(target_id, star_type)
    return create_json_response({"count": count}, 200)


@stars_bp.route('', methods=['GET'])
@token_required
def get_user_stars(current_user):
    """分页获取当前用户的所有收藏"""
    stars = StarService.get_user_stars(current_user["user_id"])
    # 动态加载关联数据
    enriched_stars = StarService.enrich_stars_data(stars)
    return create_json_response(enriched_stars, 200)


# """批量检查收藏状态？+检查单条数据是否被当前用户收藏"""
# @stars_bp.route('/batch-check', methods=['POST'])
# @jwt_required()
# def batch_check_stars():
#     current_user = get_jwt_identity()
#     model_ids = request.json.get('model_ids', [])
#
#     # 查询当前用户对这些模型的收藏记录
#     starred_models = Star.query.filter(
#         Star.user_id == current_user['id'],
#         Star.target_id.in_(model_ids),
#         Star.star_type == 'model'
#     ).all()
#
#     # 生成状态映射表
#     status_map = {str(m.target_id): True for m in starred_models}
#     return jsonify(status_map)
