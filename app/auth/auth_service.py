import jwt
from sqlalchemy.exc import SQLAlchemyError

from app.core.redis_connection_pool import redis_pool
from app.token.JWT import generate_access_token, generate_refresh_token, verify_token
from app.core.exception import ValidationError, AuthenticationError, DatabaseError, RedisConnectionError, logger
from app.exts import db
from app.user.user import User
from app.token.token_repo import TokenRepository
from app.auth.auth_repo import AuthRepository
from app.auth.login_attempt_repo import LoginAttemptsRepository
from app.core.passwd_service import PasswordService
from app.core.verify_code_service import VerificationCodeService


class AuthService:
    @staticmethod
    def register(validated_data):
        """使用已验证数据执行注册逻辑"""
        try:
            # 直接使用已验证数据（无需再次格式检查）
            login_type = validated_data['login_type']
            login_identifier = validated_data['login_identifier']

            # 验证码检查
            VerificationCodeService.validate_code(login_type, login_identifier, validated_data['code'])

            # 检查用户是否存在
            if AuthRepository.get_user_by_identifier(login_identifier, login_type):
                raise ValidationError("该用户已注册，请登录", 409)

            # 创建用户模型
            user = User(
                username=validated_data['username'],
                password=PasswordService.hashed_password(validated_data['password']),
                email=validated_data['login_identifier'] if validated_data['login_type'] == 'email' else None,
                telephone=validated_data['login_identifier'] if validated_data['login_type'] == 'telephone' else None
            )

            AuthRepository.save_user(user)
            db.session.commit()

            # 生成令牌
            return {
                "data": {
                    "user_info": user.to_dict(),
                    "access_token": generate_access_token(user.id, user.username),
                    "refresh_token": generate_refresh_token(user.id, user.username)
                },
                "message": "注册成功",
            }, 201
        except SQLAlchemyError:
            db.session.rollback()
            raise ValidationError("数据库操作失败")

    @staticmethod
    def login(validated_data):
        """
        登录服务：处理用户登录并生成 Token。
        """

        login_identifier = validated_data.get('login_identifier')
        login_type = validated_data.get('login_type')
        password = validated_data.get('password')

        # Step 1: 检查登录失败次数
        if not LoginAttemptsRepository.check_login_attempts(login_identifier):
            raise AuthenticationError("Too many login attempts. Please try again later.")

        # Step 2: 使用 Redis 锁来防止并发请求
        with redis_pool.get_redis_connection(pool_name='user') as redis_client:
            lock_key = f"lock:{login_identifier}"
            lock = redis_client.set(lock_key, 'locked', nx=True, ex=5)  # 5 秒锁
            if not lock:
                current_ttl = redis_client.ttl(lock_key)
                logger.info(f"Login lock contention for {login_identifier},TTL: {current_ttl}s")
                raise AuthenticationError("Too many users, please try again later.")

            try:
                # Step 3: 验证用户身份
                user = AuthRepository.get_user_by_identifier(login_identifier, login_type)
                if not user:  # 添加用户存在性检查
                    raise AuthenticationError("用户不存在")
                if not PasswordService.check_password(user, password):  # 密码校验
                    LoginAttemptsRepository.increment_login_attempts(login_identifier)
                    raise AuthenticationError("密码错误")

                # Step 4: 检查用户是否已有有效的 Access Token
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
                        logger.info(f"复用有效Token | user:{user.id}")
                        return {
                            "data": {
                                "user_info": user.to_dict(),
                                "access_token": stored_access_token,
                                "refresh_token": stored_refresh_token if stored_refresh_token else None
                            },
                            "message": "登录成功"
                        }, 200
                    except AuthenticationError as e:
                        TokenRepository.delete_user_token(user.id, 'access')
                        logger.warning(f"清除失效Token | user:{user.id} reason:{str(e)}")
                        logger.info(f"Error during token verification: {str(e)}")  # 输出异常信息
                        # 如果验证失败，说明 token 已过期
                        if str(e) == "Token has expired" or str(e) == "Token has been revoked":
                            pass  # 继续生成新的 token

                # Step 5: Access Token 过期，生成新的 Token，并存储新的 Access Token
                new_access_token = generate_access_token(user.id, user.username)
                TokenRepository.set_user_token(user.id, new_access_token, "access")

                # Step 6: 登录成功后，重置登录失败次数
                LoginAttemptsRepository.reset_login_attempts(login_identifier)

                logger.info(f"Login successful for {login_identifier}, generated new tokens.")
                return {
                    "data": {
                        "user_info": user.to_dict(),
                        "access_token": new_access_token,
                        "refresh_token": stored_refresh_token if stored_refresh_token else None
                    },
                    "message": "登录成功"
                }, 200

            except AuthenticationError as e:
                logger.error(f"Authentication failed for {login_identifier}: {str(e)}")
                raise e
            except RedisConnectionError as e:
                logger.error(f"Redis connection failed during login: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error during login for {login_identifier}: {str(e)}")
            finally:
                # 确保 Redis 锁被释放
                redis_client.delete(lock_key)
