from app.exts import db
from app.user.user import User


class UserRepository:

    @staticmethod
    def get_user_by_id(user_id: int) -> dict:
        """通过用户ID获取完整信息（返回字典）"""
        return User.query.get(user_id)

    @staticmethod
    def update_user_info(user_id: int, data: dict) -> dict:
        """更新用户信息（直接操作数据库）"""
        user = User.query.get(user_id)
        if not user:
            return None

        # 唯一性校验
        if 'email' in data and data['email'] != user.email:
            exists = User.query.filter_by(email=data['email']).first()
            if exists:
                raise ValueError("邮箱已被使用")

        if 'telephone' in data and data['telephone'] != user.telephone:
            exists = User.query.filter_by(telephone=data['telephone']).first()
            if exists:
                raise ValueError("手机号已被使用")

        # 直接更新字段
        for key in ['username', 'email', 'telephone']:
            if key in data:
                setattr(user, key, data[key])

        db.session.commit()
        return UserRepository.get_user_by_id(user_id)

    def delete_user_account(user_id: int) -> None:
        """删除用户账号（硬删除）"""
        user = User.query.get(user_id)
        if not user:
            return
        db.session.delete(user)
        db.session.commit()

    @staticmethod
    def search_users(filters: dict) -> dict:
        """精确搜索用户（邮箱/手机号/用户名）"""
        query = User.query

        if filters.get('email'):
            user = query.filter_by(email=filters['email']).first()
        elif filters.get('telephone'):
            user = query.filter_by(telephone=filters['telephone']).first()
        elif filters.get('username'):
            user = query.filter_by(username=filters['username']).first()
        else:
            return None

        if not user:
            return None
        return {
            "id": user.id,
            "username": user.username,
            # 根据需求隐藏部分字段（如不返回邮箱）
        }