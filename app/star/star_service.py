from typing import Dict, Any

from flask import current_app

from app.core.exception import NotFoundError, ValidationError
from app.exts import db
from app.star.star import StarType, Star
from app.star.star_repo import StarRepository


class StarService:
    @staticmethod
    def get_star_by_id(star_id: int) -> Star:
        star = StarRepository.get_star_by_id(star_id)
        if not star:
            raise NotFoundError(f"Star with ID {star_id} not found")
        return star

    @staticmethod
    def get_star_id_by_target(user_id: int, target_id: int, star_type: StarType) -> int:
        """
        获取收藏记录ID（业务逻辑层）
        :raises NotFoundError: 当收藏记录不存在时
        """
        try:
            star_id = StarRepository.get_star_id_by_target(user_id, target_id, star_type)
        except ValueError as e:
            raise ValidationError(str(e))  # 转换异常类型

        return star_id

    @staticmethod
    def add_star(validated_data):
        """
        用户添加收藏
        :param
        :return: 操作结果
        """
        try:
            user_id = validated_data['user_id']
            target_id = validated_data['target_id']
            star_type = StarType(validated_data['star_type'])  # 转换为枚举类型

            # 检查是否已收藏
            existing_star = StarService.get_star_id_by_target(user_id, target_id, star_type)
            if existing_star:
                return {"error": "You have already starred this item."}, 400
            # 创建收藏记录
            StarRepository.create_star(user_id, target_id, star_type)
            db.session.commit()
            return {'message': 'Star added successfully'}, 201
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def remove_star(validated_data):
        """
        用户取消收藏
        :param
        :return: 操作结果
        """
        user_id = validated_data['user_id']
        target_id = validated_data['target_id']
        star_type = StarType(validated_data['star_type'])  # 转换为枚举类型

        star_id = StarService.get_star_id_by_target(user_id, target_id, star_type)

        star = StarService.get_star_by_id(star_id)

        # 验证用户是否有权操作
        if star.user_id != user_id:
            raise PermissionError("无权操作此收藏")

        try:
            success = StarRepository.delete_star(star)
            db.session.commit()
            return {"message": "取消收藏成功" if success else "收藏记录不存在"}, 200
        except NotFoundError:
            db.session.rollback()
            return {"message": "收藏记录不存在"}, 404
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"删除收藏时出错: {e}", exc_info=True)  # 记录详细的错误信息
            return {"message": "服务器内部错误"}, 500

    @staticmethod
    def get_model_stars_count(model_id: int) -> int:
        """
        获取模型的收藏数
        :param model_id: 模型ID
        :return: 收藏数
        """
        return StarRepository.count_stars(model_id, StarType.MODEL)

    @staticmethod
    def get_user_model_stars(user_id: int, page: int = 1, per_page: int = 10) -> Dict[str, Any]:
        """
        获取用户收藏的模型列表（分页）
        :param user_id: 用户ID
        :param page: 页码
        :param per_page: 每页数量
        :return: 分页结果
        """
        pagination = StarRepository.get_user_stars(user_id, StarType.MODEL, page, per_page)
        return {
            "items": [star.to_dict() for star in pagination.items],
            "total": pagination.total,
            "page": page,
            "per_page": per_page
        }
