from werkzeug.security import check_password_hash


# 验证密码
def verify_password(user, password):
    """验证用户密码是否正确"""
    return check_password_hash(user.password, password)