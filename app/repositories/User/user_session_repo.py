from flask import current_app


class UserSessionRepository:
    @staticmethod
    def get_redis_client():
        """获取 Redis 客户端，默认使用 db=1"""
        redis_pool = current_app.config['REDIS_POOL']
        return redis_pool.get_redis_client('user')  # 获取用户相关数据的 Redis 连接（db=1）

    @staticmethod
    def set_user_session(user_id, session_data):
        """存储用户会话数据"""
        redis_client = UserSessionRepository.get_redis_client()
        redis_client.set(f"user_session:{user_id}", session_data)

    @staticmethod
    def get_user_session(user_id):
        """获取用户会话数据"""
        redis_client = UserSessionRepository.get_redis_client()
        return redis_client.get(f"user_session:{user_id}")

    @staticmethod
    def delete_user_session(user_id):
        """删除用户会话数据"""
        redis_client = UserSessionRepository.get_redis_client()
        redis_client.delete(f"user_session:{user_id}")
