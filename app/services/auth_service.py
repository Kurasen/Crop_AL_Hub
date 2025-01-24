from werkzeug.security import check_password_hash

class AuthService:
    @staticmethod
    # 验证密码
    def check_password(user, password):
        return check_password_hash(user.password, password)
