from app.core.redis_connection_pool import redis_pool


class TokenRepository:

    @staticmethod
    def set_user_token(user_id, token, token_type='access'):
        """
        存储用户的 JWT token，并设置过期时间。
        :param user_id: 用户 ID
        :param token: JWT token
        :param token_type: 'access' 或 'refresh'
        """
        with redis_pool.get_redis_connection(pool_name='user') as redis_client:
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
        with redis_pool.get_redis_connection(pool_name='user') as redis_client:
            token_key = f"user_{user_id}_token:{token_type}"
            return redis_client.get(token_key)

    @staticmethod
    def delete_user_token(user_id, token_type='access'):
        """
        删除用户的指定类型 token。
        :param user_id: 用户 ID
        :param token_type: 'access' 或 'refresh'
        """
        with redis_pool.get_redis_connection(pool_name='user') as redis_client:
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
        with redis_pool.get_redis_connection(pool_name='user') as redis_client:
            token_key = f"user_{user_id}_token:{token_type}"
            return redis_client.exists(token_key)
