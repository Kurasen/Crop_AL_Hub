from werkzeug.security import check_password_hash

from app.blueprint.utils.JWT import generate_token
from app.blueprint.utils.auth_utils import verify_password
from app.repositories.User.auth_repo import AuthRepository
from app.repositories.User.login_attempt_repo import LoginAttemptsRepository


class AuthService:

    @staticmethod
    def login(data):
        """
        登录服务：处理用户登录并生成 Token。
        """
        login_identifier = data['login_identifier']
        login_type = data['login_type']
        password = data['password']

        # # Step 1: 检查登录格式
        # format_check = AuthRepository.validate_username_format(login_type, login_identifier)
        # if format_check:
        #     return format_check  # 如果格式不正确，返回错误信息
        #
        # # Step 2: 验证密码格式
        # is_valid, message = AuthRepository.validate_password_format(password)
        # if not is_valid:
        #     return {"message": message}, 400  # 如果密码不符合要求，返回错误信息

        # Step 3: 检查登录失败次数
        if not LoginAttemptsRepository.check_login_attempts(login_identifier):
            return {"message": "Too many login attempts. Please try again later."}, 429

        # Step 4: 使用 Redis 锁来防止并发请求
        redis_client = AuthRepository.get_redis_client()
        lock_key = f"lock:{login_identifier}"
        lock = redis_client.set(lock_key, 'locked', nx=True, ex=5)  # 5 秒锁
        if not lock:
            return {"message": "Too many users, please try again later."}, 429

        try:
            # Step 5: 调用 AuthRepository 验证用户身份
            user = AuthRepository.login_user(login_identifier, login_type, password)
            if not user:
                # 登录失败，增加登录尝试次数
                LoginAttemptsRepository.increment_login_attempts(login_identifier)
                return {"message": "Invalid username or password"}, 401

            # Step 6: 登录成功，重置尝试次数并生成 Token
            LoginAttemptsRepository.reset_login_attempts(login_identifier)
            token = generate_token(user.id, user.username)
            return {"message": "Login successful", "token": token}, 200

        finally:
            # 确保释放锁
            redis_client.delete(lock_key)

    @staticmethod
    # 验证密码
    def check_password(user, password):
        return check_password_hash(user.password, password)

    @staticmethod
    def authenticate_user(login_identifier, login_type, password):
        user = AuthRepository.get_user_by_identifier(login_identifier, login_type)

        if user and verify_password(user, password):
            return user, None
        return None, "Invalid username or password"

    @staticmethod
    def generate_jwt(user):
        return generate_token(user.id, user.username)