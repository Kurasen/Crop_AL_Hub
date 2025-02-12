from flask import request, Blueprint
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from app.blueprint.utils.JWT import token_required, add_to_blacklist, get_jwt_identity, verify_token
from app.exception.errors import ValidationError, DatabaseError, AuthenticationError, logger
from app.repositories.Token.token_repo import TokenRepository
from app.services.auth_service import AuthService

user_bp = Blueprint('auth', __name__)


@user_bp.route('/login', methods=['POST'])
def login():
    """
    用户登录 API
    ---
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            login_identifier:
              type: string
              description: 用户的用户名、邮箱或电话号码
            login_type:
              type: string
              description: 登录类型（选择：用户名、邮箱或电话号码）
              enum:
                - username
                - email
                - telephone  # 提供选择框
            password:
              type: string
              description: 用户的密码
    responses:
      200:
        description: Successfully logged in.
        schema:
          type: object
          properties:
            access_token:
              type: string
            refresh_token:
              type: string
      400:
        description: Invalid username or password.
    """
    if not request.is_json:
        raise ValidationError("Request must be JSON")
    data = request.get_json()

    try:
        response, status = AuthService.login(data)
        return response, status
    except (IntegrityError, OperationalError, SQLAlchemyError):
        raise DatabaseError("Database error occurred. Please try again later.")

@user_bp.route('/logout', methods=['POST'])
@token_required  # 使用装饰器，确保用户已认证
def post(current_user):
    """登出功能"""
    # 获取当前用户的 ID
    user_id = current_user['user_id']
    jti = get_jwt_identity()

    # 将 Access Token 加入黑名单
    add_to_blacklist(jti)

    # 删除 Refresh Token
    TokenRepository.delete_user_token(user_id, token_type='refresh')

    logger.info(f"User {user_id} successfully logged out.")
    return {"message": "Logout successful"}, 200


# 受保护接口：需要使用 JWT 认证
@user_bp.route('/protected', methods=['GET'])
@token_required  # 使用装饰器，确保用户已认证
def protected_route(current_user):
    """受保护接口"""
    if not isinstance(current_user, dict) or 'username' not in current_user:
        raise ValidationError("Invalid user data")
    return {"message": f"Hello, {current_user['username']}!"}, 200


@user_bp.route('/refresh_token', methods=['POST'])
def refresh_token():
    """刷新 Token"""
    print(f"Request Headers: {request.headers}")  # 打印请求头信息
    token = request.headers.get('Authorization')
    if not token:
        raise ValidationError("Token is missing")
    # 处理 Bearer 头
    if token.startswith('Bearer '):
        token = token[len('Bearer '):]
    # 如果 Token 不以 "Bearer " 开头，直接使用它
    token = token.strip()  # 确保没有多余的空格

    # 验证 token 类型
    try:
        decoded = verify_token(token)
        token_type = decoded.get('token_type')

        # 如果是 access_token，则返回错误提示
        if token_type == 'access':
            raise AuthenticationError("Access token cannot be used to refresh the token. Please use a valid "
                                      "refresh token.")

    except AuthenticationError as e:
        logger.error(f"Token refresh failed: {str(e)}")
        raise e

    try:
        # 验证 refresh_token 并获取新的 access_token
        response, status = AuthService.refresh_token(token)
        return response, status
    except AuthenticationError as e:
        # 记录刷新 Token 失败的日志
        logger.error(f"Token refresh failed: {str(e)}")
        raise e
