from sqlalchemy.exc import SQLAlchemyError
from app.blueprint.utils.JWT import generate_access_token, generate_refresh_token, verify_token
from app.exception.errors import ValidationError, AuthenticationError, DatabaseError
from app.exts import db
from app.models.user import User
from app.repositories.Token.token_repo import TokenRepository
from app.repositories.Auth.auth_repo import AuthRepository
from app.repositories.Auth.login_attempt_repo import LoginAttemptsRepository
from flask import current_app
from app.services.Auth.input_format import InputFormatService
from app.services.Auth.passwd_service import PasswordService
from app.services.Auth.verify_code_service import VerificationCodeService


class AuthService:

    @staticmethod
    def register(data):
        """
        用户注册接口：检查手机号/邮箱是否已注册，验证码是否正确，并注册新用户
        """
        try:
            # Step 1: 输入验证，确保必填字段存在
            required_fields = ['login_type', 'login_identifier', 'username', 'password', 'code']
            InputFormatService.validate_required_fields(data, required_fields)

            login_type = data.get('login_type')  # 注册方式，'telephone' 或 'email'
            login_identifier = data.get('login_identifier')
            username = data.get('username')
            password = data.get('password')
            code = data.get("code")  # 用户输入的验证码

            # Step 1: 验证格式（手机号或邮箱）,密码。校验login_type是否为电话或邮箱
            if login_type not in ['telephone', 'email']:
                raise ValidationError("Invalid login type. Only 'telephone' or 'email' are allowed.")
            InputFormatService.validate_credentials_format(login_type, login_identifier, password)

            print(f"Password before hashing: {password} (type: {type(password)})")  # 调试打印密码类型

            # Step 2: 验证验证码
            VerificationCodeService.validate_code(login_type, login_identifier, code)

            # Step 3: 检查是否已注册（根据 login_type）
            if AuthRepository.get_user_by_identifier(login_identifier, login_type):
                raise ValidationError(f"{login_type.capitalize()} is already registered.")

            # Step 4: 创建用户名
            hashed_password = PasswordService.hashed_password(password)
            print(f"Hashed password type: {type(hashed_password)}")
            user = User(username=username, password=hashed_password,
                        email=login_identifier if login_type == 'email' else None,
                        telephone=login_identifier if login_type == 'telephone' else None)
            AuthRepository.save_user(user)  # 保存到数据库

            # Step 4: 生成 Token
            access_token = generate_access_token(user.id, user.username)
            refresh_token = generate_refresh_token(user.id, user.username)

            return {
                "message": "Auth registered successfully",
                "access_token": access_token,
                "refresh_token": refresh_token
            }, 201
        except (ValidationError, SQLAlchemyError) as e:
            # 回滚事务，如果发生错误
            db.session.rollback()
            current_app.logger.error(f"Error during registration: {str(e)}")
            raise e  # 抛出异常以便全局异常处理类捕获

        finally:
            # 关闭数据库会话
            db.session.remove()  # 用 remove() 来确保会话释放

    @staticmethod
    def login(data):
        """
        登录服务：处理用户登录并生成 Token。
        """
        # Step 1: 确保必填字段存在
        required_fields = ['login_type', 'login_identifier', 'password']
        InputFormatService.validate_required_fields(data, required_fields)

        login_identifier = data.get('login_identifier')
        login_type = data.get('login_type')
        password = data.get('password')

        # Step 1: 校验login_type是否为电话或邮箱
        if login_type not in ['telephone', 'email']:
            raise ValidationError("Invalid login type. Only 'telephone' or 'email' are allowed.")

        # Step 2: 验证登录信息格式（手机号/邮箱 和 密码）
        InputFormatService.validate_credentials_format(login_type, login_identifier, password)

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
            if not user:  # 添加用户存在性检查
                raise AuthenticationError("User does not exist")
            if not PasswordService.check_password(user, password):  # 密码校验
                LoginAttemptsRepository.increment_login_attempts(login_identifier)
                raise AuthenticationError("Invalid username or password")

            # Step 6: 检查用户是否已有有效的 Access Token
            stored_access_token = TokenRepository.get_user_token(user.id, "access")
            stored_refresh_token = TokenRepository.get_user_token(user.id, "refresh")

            if not stored_refresh_token:
                stored_refresh_token = generate_refresh_token(user.id, user.username)
                TokenRepository.set_user_token(user.id, stored_refresh_token, "refresh")

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
                    current_app.logger.info(f"Auth {login_identifier} already has a valid access token.")
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
