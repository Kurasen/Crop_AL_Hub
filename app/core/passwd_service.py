import bcrypt


class PasswordService:
    @staticmethod
    def check_password(user, password):
        """验证密码"""
        return bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8'))

    @staticmethod
    def hashed_password(plain_password):
        """
        对传入的明文密码进行加密。

        :param plain_password: 明文密码
        :return: 加密后的密码
        """
        # 使用 generate_password_hash 对传入的密码进行加密
        hashed_password = bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt())
        return hashed_password.decode('utf-8')
