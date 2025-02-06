from werkzeug.security import check_password_hash

from app.blueprint.utils.JWT import generate_token
from app.blueprint.utils.auth_utils import verify_password
from app.repositories.User.auth_repo import AuthRepository
from app.repositories.User.login_attempt_repo import LoginAttemptsRepository


class AuthService:

    @staticmethod
    def login(data):
        login_identifier = data['login_identifier']
        login_type = data['login_type']
        password = data['password']

        # 检查输入格式
        AuthRepository.validate_username_format(login_type, login_identifier)

        # 验证密码强度
        is_valid, message = AuthRepository.validate_password_format(password)
        if not is_valid:
            return {"message": message}, 400

        # 检查登录失败次数
        if not LoginAttemptsRepository.check_login_attempts(login_identifier):
            return {"message": "Too many login attempts. Please try again later."}, 429

        # 获取用户
        user = AuthRepository.get_user_by_identifier(login_identifier, login_type)

        # 检查用户是否存在以及密码是否正确
        if not user or not verify_password(user, password):
            LoginAttemptsRepository.increment_login_attempts(login_identifier)
            return {"message": "Invalid username or password"}, 401
        else:
            LoginAttemptsRepository.reset_login_attempts(login_identifier)

        # 生成 JWT Token
        token = generate_token(user.id, user.username)
        return {"message": "Login successful", "token": token}, 200


    @staticmethod
    # 验证密码
    def check_password(user, password):
        return check_password_hash(user.password, password)

    @staticmethod
    def authenticate_user(login_identifier, login_type, password):
        # 根据 login_type 查找用户
        if login_type == 'username':
            user = AuthRepository.get_user_by_username(login_identifier)
        elif login_type == 'telephone':
            user = AuthRepository.get_user_by_telephone(login_identifier)
        elif login_type == 'email':
            user = AuthRepository.get_user_by_email(login_identifier)
        else:
            return None, "Invalid login type"

        # 检查用户是否存在且密码是否正确
        if user and check_password_hash(user.password, password):
            return user, None
        return None, "Invalid username or password"

    @staticmethod
    def generate_jwt(user):
        return generate_token(user.id, user.username)