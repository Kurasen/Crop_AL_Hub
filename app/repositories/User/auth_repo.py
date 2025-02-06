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
        登录用户，检查用户的登录信息并限制登录尝试次数。
        """

        # Step 1: 检查登录次数限制
        if not LoginAttemptsRepository.check_login_attempts(login_identifier):
            return {"message": "Too many login attempts. Please try again later."}, 429

        # Step 2: 使用 Redis 锁来防止并发请求
        redis_client = AuthRepository.get_redis_client()
        lock_key = f"lock:{login_identifier}"
        lock = redis_client.set(lock_key, 'locked', nx=True, ex=5)  # 5 秒锁
        if not lock:
            return "Too many users, please try again later.", 429

        try:
            # Step 3: 验证用户的登录信息
            user = AuthRepository.get_user_by_identifier(login_identifier, login_type)
            if not user or not verify_password(user, password):
                # 登录失败，增加登录尝试次数
                LoginAttemptsRepository.increment_login_attempts(login_identifier)
                return {"message": "Invalid credentials"}, 401

            # 登录成功，重置尝试次数
            LoginAttemptsRepository.reset_login_attempts(login_identifier)

            # 生成 Token
            token = generate_token(user.id, user.username)
            return {"message": "Login successful", "token": token}, 200
        except (IntegrityError, OperationalError, SQLAlchemyError) as e:
            # 捕获数据库异常
            return {"message": f"Database error: {str(e)}"}, 500
        finally:
            # 确保释放锁
            redis_client.delete(lock_key)


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