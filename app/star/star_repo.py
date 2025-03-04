from sqlalchemy import and_

from app.exts import db
from app.star.star import StarType, Star


class StarRepository:
    @staticmethod
    def get_star_by_id(star_id):
        return Star.query.get(star_id)

    @staticmethod
    def get_star_id_by_target(user_id: int, target_id: int, star_type: StarType) -> int | None:
        """
        根据用户ID、目标ID和收藏类型获取收藏记录ID（优化版）
        :param user_id: 用户ID
        :param target_id: 目标ID（模型/数据集等）
        :param star_type: 收藏类型（model/dataset）
        :return: star_id 或 None（未找到时）
        """
        # 定义类型到字段的映射（避免硬编码）
        type_field_map = {
            StarType.MODEL: 'model_id',
            StarType.DATASET: 'dataset_id'
        }
        # 动态获取查询字段
        target_field = type_field_map[star_type]

        # 3. 校验模型字段是否存在（防止拼写错误）
        if not hasattr(Star, target_field):
            raise AttributeError(f"Star模型不存在字段: {target_field}")

        # 4. 构建查询（仅获取id字段，提升性能）
        star = Star.query.with_entities(Star.id).filter(
            Star.user_id == user_id,
            getattr(Star, target_field) == target_id,
            Star.star_type == star_type.value  # 假设数据库存储枚举的value值
        ).first()

        return star.id if star else None

    @staticmethod
    def create_star(user_id: int, target_id: int, star_type: StarType) -> Star:
        """
        创建收藏记录
        :param user_id: 用户ID
        :param target_id: 目标ID（模型ID或数据集ID）
        :param star_type: 收藏类型（MODEL 或 DATASET）
        :return: Star 对象
        """
        star = Star(
            user_id=user_id,
            model_id=target_id if star_type == StarType.MODEL else None,
            dataset_id=target_id if star_type == StarType.DATASET else None,
            star_type=star_type
        )
        db.session.add(star)
        return star

    @staticmethod
    def delete_star(star):
        """删除模型"""
        if not star:
            raise ValueError("传入的模型为空")
        db.session.delete(star)
        return True