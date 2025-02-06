from flask import current_app


class TokenRepository:
    @staticmethod
    def get_redis_client():
        """获取 Redis 客户端，默认使用 db=1"""
        redis_pool = current_app.config['REDIS_POOL']
        return redis_pool.get_redis_client('user')  # 获取用户相关数据的 Redis 连接（db=1）

    @staticmethod
    def set_user_token(user_id, token):
        """存储用户的 JWT token"""
        redis_client = TokenRepository.get_redis_client()
        redis_client.set(f"user_token:{user_id}", token, ex=3600)  # token 有效期为 1 小时

    @staticmethod
    def get_user_token(user_id):
        """获取用户的 JWT token"""
        redis_client = TokenRepository.get_redis_client()
        return redis_client.get(f"user_token:{user_id}")

    @staticmethod
    def delete_user_token(user_id):
        """删除用户的 JWT token"""
        redis_client = TokenRepository.get_redis_client()
        redis_client.delete(f"user_token:{user_id}")
