import re

from werkzeug.security import check_password_hash

from app.blueprint.utils.JWT import generate_access_token, generate_refresh_token
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

            # Step 6: 检查是否已经有有效的 Token 存储在 Redis 中
            token = TokenRepository.get_user_token(user.id)
            if token:
                current_app.logger.info(f"Login successful for {login_identifier}, token already exists.")
                return {"message": "Login successful", "token": token}, 200

            # Step 7: 登录成功，重置登录次数，生成 Token
            LoginAttemptsRepository.reset_login_attempts(login_identifier)
            access_token = generate_access_token(user.id, user.username)
            refresh_token = generate_refresh_token(user.id, user.username)

            # Step 8:存储 Token 到 Redis
            TokenRepository.set_user_token(user.id, access_token)
            TokenRepository.set_user_token(user.id, refresh_token, 'refresh')

            current_app.logger.info(f"Login successful for {login_identifier}, generated new tokens.")
            return {"message": "Login successful", "token": access_token}, 200

        except AuthenticationError as e:
            current_app.logger.error(f"Authentication failed for {login_identifier}: {str(e)}")
            raise e
        except Exception as e:
            current_app.logger.error(f"Unexpected error during login for {login_identifier}: {str(e)}")
            raise DatabaseError("Internal error occurred while logging in.")
        finally:
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
    def refresh_token(token):
        """
        刷新 Token，调用 AuthRepository 的 refresh_token 方法。
        :param token: 旧的 JWT Token
        :return: 新的 Access Token 或错误信息
        """
        return AuthRepository.refresh_token(token)
