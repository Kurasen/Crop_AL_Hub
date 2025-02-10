import re

from werkzeug.security import check_password_hash

from app.blueprint.utils.JWT import generate_access_token, generate_refresh_token, verify_token
from app.exception.errors import ValidationError, AuthenticationError, DatabaseError
from app.repositories.Token.token_repo import TokenRepository
from app.repositories.User.auth_repo import AuthRepository
from app.repositories.User.login_attempt_repo import LoginAttemptsRepository
from flask import current_app


class AuthService:

    @staticmethod
    def login(data):
        """
        登录服务：处理用户登录并生成 Token。
        """
        login_identifier = data['login_identifier']
        login_type = data['login_type']
        password = data['password']

        # # Step 1: 校验输入格式
        # format_check = AuthService.validate_username_format(login_type, login_identifier)
        # if format_check:
        #     raise ValidationError(f"Invalid {login_type} format")
        #
        # # Step 2: 校验密码格式
        # is_valid, message = AuthService.validate_password_format(password)
        # if not is_valid:
        #     raise ValidationError(message)

        # Step 3: 检查登录失败次数
        if not LoginAttemptsRepository.check_login_attempts(login_identifier):
            raise AuthenticationError("Too many login attempts. Please try again later.")

        # Step 4: 使用 Redis 锁来防止并发请求
        redis_client = AuthRepository.get_redis_client()
        lock_key = f"lock:{login_identifier}"
        lock = redis_client.set(lock_key, 'locked', nx=True, ex=5)  # 5 秒锁
        if not lock:
            raise AuthenticationError("Too many users, please try again later.")

        try:
            # Step 5: 验证用户身份
            user = AuthRepository.get_user_by_identifier(login_identifier, login_type)
            if not AuthService.check_password(user, password):  # 密码校验
                LoginAttemptsRepository.increment_login_attempts(login_identifier)
                raise AuthenticationError("Invalid username or password")

            # Step 6: 检查用户是否已有有效的 Access Token
            stored_access_token = TokenRepository.get_user_token(user.id, "access")
            stored_refresh_token = TokenRepository.get_user_token(user.id, "refresh")

            print(f"Stored access token: {stored_access_token}")  # 输出当前存储的 access_token

            if not stored_refresh_token:
                stored_refresh_token = generate_refresh_token(user.id, user.username)
                TokenRepository.set_user_token(user.id, stored_refresh_token, "refresh")

            print(stored_access_token, stored_refresh_token)

            # 如果 Redis 返回的是 bytes 类型，转换成字符串
            if isinstance(stored_access_token, bytes):
                stored_access_token = stored_access_token.decode("utf-8")
            if isinstance(stored_refresh_token, bytes):
                stored_refresh_token = stored_refresh_token.decode("utf-8")

            # 如果已经有有效的 access_token，则直接使用
            if stored_access_token:
                try:
                    # 验证 access_token 是否有效并且没有被撤销
                    verify_token(stored_access_token, check_blacklist=True)
                    print(f"Access token for {login_identifier} is valid and not revoked.")  # 输出验证成功的信息
                    current_app.logger.info(f"User {login_identifier} already has a valid access token.")
                    return {
                        "message": "Login successful",
                        "access_token": stored_access_token,
                        "refresh_token": stored_refresh_token if stored_refresh_token else None
                    }, 200
                except AuthenticationError as e:
                    print(f"Error during token verification: {str(e)}")  # 输出异常信息
                    # 如果验证失败，说明 token 已过期
                    if str(e) == "Token has expired" or str(e) == "Token has been revoked":
                        pass  # 继续生成新的 token

            # Step 7: Access Token 过期，生成新的 Token，并存储新的 Access Token
            new_access_token = generate_access_token(user.id, user.username)
            TokenRepository.set_user_token(user.id, new_access_token, "access")

            # Step 8: 登录成功后，重置登录失败次数
            LoginAttemptsRepository.reset_login_attempts(login_identifier)

            current_app.logger.info(f"Login successful for {login_identifier}, generated new tokens.")
            return {
                "message": "Login successful",
                "access_token": new_access_token,
                "refresh_token": stored_refresh_token if stored_refresh_token else None
            }, 200

        except AuthenticationError as e:
            current_app.logger.error(f"Authentication failed for {login_identifier}: {str(e)}")
            raise e
        except Exception as e:
            current_app.logger.error(f"Unexpected error during login for {login_identifier}: {str(e)}")
            raise DatabaseError("Internal error occurred while logging in.")
        finally:
            # 确保 Redis 锁被释放
            redis_client.delete(lock_key)

    @staticmethod
    def check_password(user, password):
        """验证密码"""
        return check_password_hash(user.password, password)

    @staticmethod
    def authenticate_user(login_identifier, login_type, password):
        """验证用户身份"""
        user = AuthRepository.get_user_by_identifier(login_identifier, login_type)
        if not AuthService.check_password(user, password):
            raise AuthenticationError("Invalid username or password")
        return user

    @staticmethod
    def generate_jwt(user):
        """生成 JWT Token"""
        return generate_access_token(user.id, user.username)

    # 验证输入格式
    @staticmethod
    def validate_username_format(login_type, login_identifier):
        """验证用户名、电话或邮箱格式"""
        patterns = {
            'username': r'^[a-zA-Z0-9_]{3,20}$',
            'telephone': r'^\+?[0-9]{10,15}$',
            'email': r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        }
        if not re.match(patterns.get(login_type, ""), login_identifier):
            return False
        return True

    # 验证密码格式
    @staticmethod
    def validate_password_format(password):
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        if not re.search(r'[A-Z]', password):  # 至少一个大写字母
            return False, "Password must contain at least one uppercase letter"
        if not re.search(r'[a-z]', password):  # 至少一个小写字母
            return False, "Password must contain at least one lowercase letter"
        if not re.search(r'[0-9]', password):  # 至少一个数字
            return False, "Password must contain at least one number"
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):  # 至少一个特殊字符
            return False, "Password must contain at least one special character"
        return True, ""

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
            raise AuthenticationError("Refresh Token is invalid or has been revoked")

        # 生成新的 Access Token 和新的 Refresh Token
        new_access_token = generate_access_token(user_id, username)
        new_refresh_token = generate_refresh_token(user_id, username)

        # 删除旧的 Refresh Token 并存储新的
        TokenRepository.delete_user_token(user_id, 'refresh')
        TokenRepository.set_user_token(user_id, new_refresh_token, 'refresh')

        return {"message": "Token refreshed", "access_token": new_access_token, "refresh_token": new_refresh_token}, 200
