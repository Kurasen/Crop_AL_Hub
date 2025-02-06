import re

import jwt

from app.blueprint.utils.JWT import verify_token, generate_token
from app.models.user import User


class AuthRepository:
    """
    认证服务层，负责处理用户的登录验证、密码校验、Token刷新等业务逻辑。
    """

    # 根据用户提供的登录类型查询用户
    @staticmethod
    def get_user_by_identifier(login_identifier, login_type):
        if login_type == 'username':
            return User.query.filter_by(username=login_identifier).first()
        elif login_type == 'telephone':
            return User.query.filter_by(telephone=login_identifier).first()
        elif login_type == 'email':
            return User.query.filter_by(email=login_identifier).first()
        return None

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
        if login_type == 'username' and not re.match(r'^[a-zA-Z0-9_]{3,20}$', login_identifier):
            return {"message": "Invalid username format"}, 400
        elif login_type == 'telephone' and not re.match(r'^\+?[0-9]{10,15}$', login_identifier):
            return {"message": "Invalid telephone format"}, 400
        elif login_type == 'email' and not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$',
                                                    login_identifier):
            return {"message": "Invalid email format"}, 400

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

    def refresh_token(token):
        """
        使用 Refresh Token 获取新的 Access Token。

        :param refresh_token: 用户的 Refresh Token
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

