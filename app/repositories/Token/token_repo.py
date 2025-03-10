from flask import current_app


def list_all_tokens():
    """列出所有用户的 Token（仅用于管理）"""
    redis_client = TokenRepository.get_redis_client()
    # 获取所有与 user_*_token:* 相关的 Redis 键
    keys = redis_client.keys("user_*_token:*")
    return {key.decode('utf-8'): redis_client.get(key).decode('utf-8') for key in keys}


class TokenRepository:
    @staticmethod
    def get_redis_client():
        """获取 Redis 客户端，默认使用 db=1"""
        redis_pool = current_app.config['REDIS_POOL']
        return redis_pool.get_redis_client('user')  # 获取用户相关数据的 Redis 连接（db=1）

    @staticmethod
    def set_user_token(user_id, token, token_type='access'):
        """
        存储用户的 JWT token，并设置过期时间。
        :param user_id: 用户 ID
        :param token: JWT token
        :param token_type: 'access' 或 'refresh'
        """
        redis_client = TokenRepository.get_redis_client()

        # 为了避免重复，存储时附加 'user_{user_id}_token:{token_type}'
        token_key = f"user_{user_id}_token:{token_type}"

        if token_type == 'access':
            redis_client.set(token_key, token, ex=900)  # access_token 有效期为 15 分钟
        elif token_type == 'refresh':
            redis_client.set(token_key, token, ex=604800)  # refresh_token 有效期为 7 天
        else:
            raise ValueError("Invalid token type. Use 'access' or 'refresh'.")

    @staticmethod
    def get_user_token(user_id, token_type='access'):
        """
        获取用户的 JWT token。
        :param user_id: 用户 ID
        :param token_type: 'access' 或 'refresh'
        :return: 返回存储的 token 或 None
        """
        redis_client = TokenRepository.get_redis_client()
        token_key = f"user_{user_id}_token:{token_type}"
        return redis_client.get(token_key)

    @staticmethod
    def delete_user_token(user_id, token_type='access'):
        """
        删除用户的指定类型 token。
        :param user_id: 用户 ID
        :param token_type: 'access' 或 'refresh'
        """
        redis_client = TokenRepository.get_redis_client()
        token_key = f"user_{user_id}_token:{token_type}"
        redis_client.delete(token_key)

    @staticmethod
    def token_exists_in_redis(user_id, token_type='access'):
        """
        检查用户的指定类型 token 是否存在 Redis 中。
        :param user_id: 用户 ID
        :param token_type: 'access' 或 'refresh'
        :return: True 如果存在，False 如果不存在
        """
        redis_client = TokenRepository.get_redis_client()
        token_key = f"user_{user_id}_token:{token_type}"
        return redis_client.exists(token_key)
