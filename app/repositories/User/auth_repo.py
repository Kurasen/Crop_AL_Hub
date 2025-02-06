import re
import jwt
from app.blueprint.utils.JWT import verify_token, generate_token
from app.blueprint.utils.auth_utils import verify_password
from app.models.user import User
from app.repositories.User.login_attempt_repo import LoginAttemptsRepository
from flask import current_app
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError


class AuthRepository:
    """
    认证服务层，负责处理用户的登录验证、密码校验、Token刷新等业务逻辑。
    """

    @staticmethod
    def get_redis_client():
        """获取 Redis 客户端，默认使用 db=1"""
        redis_pool = current_app.config['REDIS_POOL']
        return redis_pool.get_redis_client('user')  # 获取用户登录相关数据的 Redis 连接（db=1）

    # 根据用户提供的登录类型查询用户
    @staticmethod
    def get_user_by_identifier(login_identifier, login_type):
        """根据用户提供的登录类型查询用户"""
        filters = {
            'username': User.username,
            'telephone': User.telephone,
            'email': User.email
        }
        return User.query.filter(filters.get(login_type) == login_identifier).first()

    # 根据用户名来查询用户
    @staticmethod
    def get_user_by_username(username):
        return User.query.filter_by(username=username).first()

    # 根据电话号码来查询用户
    @staticmethod
    def get_user_by_telephone(telephone):
        return User.query.filter_by(telephone=telephone).first()

    # 根据邮箱来查询用户
    @staticmethod
    def get_user_by_email(email):
        return User.query.filter_by(email=email).first()

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
            return {"message": f"Invalid {login_type} format"}, 400
        return None

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
    def login_user(login_identifier, login_type, password):
        """
        根据 login_identifier 和 login_type 验证用户身份，并校验密码是否正确
        :param login_identifier: 用户名/电话/邮箱
        :param login_type: 登录方式（username, telephone, email）
        :param password: 用户密码
        :return: 用户对象或 None，如果找不到用户或密码不匹配
        """
        user = AuthRepository.get_user_by_identifier(login_identifier, login_type)
        if user and verify_password(user, password):  # 密码匹配
            return user
        return None  # 用户未找到或密码错误

    def refresh_token(token):
        """
        使用 Refresh Token 获取新的 Access Token。
        :return: 返回新的 Access Token，或者错误信息
        """
        try:
            decoded = verify_token(token)  # 解码并验证 JWT
            new_token = generate_token(decoded['user_id'], decoded['username'])
            return {"message": "Token refreshed", "token": new_token}, 200
        except jwt.ExpiredSignatureError:
            return {"message": "Token has expired. Please log in again."}, 401
        except jwt.InvalidTokenError:
            return {"message": "Invalid token. Please log in again."}, 401
