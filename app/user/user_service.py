from app.core.exception import NotFoundError
from app.user.user_repo import UserRepository


class UserService:
    @staticmethod
    def get_user_by_id(user_id):
        # 获取指定ID的user
        user = UserRepository.get_user_by_id(user_id)
        if not user:
            raise NotFoundError(f"Dataset with ID {user_id} not found")
        return user

    @staticmethod
    def search_users(search_data):
        """用户搜索服务"""
        identity = (
                search_data.username
                or search_data.telephone
                or search_data.email
        )

        users = UserRepository.search_users(identity)
        return {
            "count": len(users),
            "users": users
        }
