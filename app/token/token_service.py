from app.core.exception import AuthenticationError, TokenError
from app.token.JWT import verify_token, generate_access_token, generate_refresh_token
from app.token.token_repo import TokenRepository


class TokenService:
    @staticmethod
    def refresh_token(old_refresh_token):
        """
        使用 refresh_token 获取新的 access_token
        """
        # 验证并解码旧的 refresh_token
        decoded = verify_token(old_refresh_token)
        user_id = decoded['user_id']
        username = decoded['username']

        # 检查 Refresh Token 是否仍然有效
        stored_refresh_token = TokenRepository.get_user_token(user_id, "refresh")

        # 如果 stored_refresh_token 是 bytes 类型，则需要解码
        if isinstance(stored_refresh_token, bytes):
            stored_refresh_token = stored_refresh_token.decode("utf-8")

        # 验证 refresh_token 是否一致
        if not stored_refresh_token or stored_refresh_token != old_refresh_token:
            raise TokenError("Refresh Token is invalid or has been revoked")

        # 生成新的 Access Token 和新的 Refresh Token
        new_access_token = generate_access_token(user_id, username)
        new_refresh_token = generate_refresh_token(user_id, username)

        # 删除旧的 Refresh Token 并存储新的
        TokenRepository.delete_user_token(user_id, 'refresh')
        TokenRepository.set_user_token(user_id, new_refresh_token, 'refresh')

        return {"message": "Token refreshed", "access_token": new_access_token, "refresh_token": new_refresh_token}, 200