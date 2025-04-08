import bcrypt
from bcrypt import checkpw, gensalt, hashpw

from app.core.exception import logger


class PasswordService:
    @staticmethod
    def check_password(user, password):
        """验证密码"""
        try:
            # 关键修复：先验证哈希值的合法性
            if not user.password.startswith("$2b$"):
                raise ValueError("无效的密码哈希格式")

            return checkpw(
                password.encode('utf-8'),
                user.password.encode('utf-8')
            )
        except (ValueError, AttributeError) as e:
            # 记录具体错误类型
            logger.error(f"密码验证失败: {str(e)}")
            return False

    @staticmethod
    def hashed_password(plain_password):
        # 明确指定 bcrypt 版本（避免兼容性问题）
        salt = gensalt(rounds=12, prefix=b'2b')  # 强制使用 $2b$ 格式
        hashed = hashpw(plain_password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
