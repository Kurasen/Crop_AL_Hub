from flask import Blueprint, request, jsonify
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash
from app.blueprint.utils.JWT import generate_token, token_required
from flask_restx import Resource, Api, fields
from app.models.user import User

# 创建 Blueprint 和 URL 前缀
auth_bp = Blueprint('auth', __name__)
# 定义 Flask-RESTX 的 API 文档对象
api = Api(version='1.0', title='Flask Login API', description='Login functionality with JWT')
# 定义命名空间
auth_ns = api.namespace('auth', description='Operations related to auth')

# 定义 Swagger 接口参数模型
login_model = api.model('Login', {
    'login_identifier': fields.String(required=True, description='Username, telephone, or email for login'),
    'login_type': fields.String(required=True, description='The type of login: username, telephone, or email'),
    'password': fields.String(required=True, description='The password for login')
})

# 注册模型
api.models['Login'] = login_model


@auth_ns.route('/login')  # 这里是直接定义接口路由
class LoginResource(Resource):
    @api.doc(description='Login and get a JWT token')
    @api.expect(login_model)  # 绑定 Swagger 文档模型
    def post(self):
        try:
            # 检查 Content-Type 是否为 JSON
            if not request.is_json:
                return {"message": "Request must be of type JSON"}, 400
            # 从请求中获取数据
            data = request.get_json()
            if not data:
                return {"message": "Request body must be a valid JSON"}, 400

            # 检查必需字段是否存在且非空
            missing_fields = [field for field in ['login_identifier', 'password', 'login_type'] if not data.get(field)]
            if missing_fields:
                return {"message": f"Missing fields: {', '.join(missing_fields)}"}, 400

            login_identifier = data['login_identifier']
            login_type = data['login_type']
            password = data['password']

            # 根据 login_type 查询对应字段
            if login_type == 'username':
                user = User.query.filter_by(username=login_identifier).first()
            elif login_type == 'telephone':
                user = User.query.filter_by(telephone=login_identifier).first()
            elif login_type == 'email':
                user = User.query.filter_by(email=login_identifier).first()
            else:
                return {"message": "Invalid login type"}, 400  # 如果传递的 login_type 不合法

            # 检查用户是否存在以及密码是否正确
            if not user or not check_password_hash(user.password, password):
                return {"message": "Invalid username or password"}, 401

            # 生成 JWT
            token = generate_token(user.id, user.username)
            return {"message": "Login successful", "token": token}, 200

        except ValueError as ve:
            return {"message": f"Invalid input: {str(ve)}"}, 400

        except SQLAlchemyError as db_error:
            # 捕获数据库相关错误
            return {"message": "Database error occurred. Please try again later."}, 500

        except Exception as e:
            # 捕获其他未预期的异常
            return {"message": f"An unexpected error occurred: {str(e)}"}, 500

    def get(self):
        return {"message": "Use POST method to login"}, 200


# 受保护接口：需要使用 JWT 认证
@auth_ns.route('/protected')
class ProtectedRoute(Resource):
    @api.doc(description='Protected route, requires JWT token')
    @token_required  # 使用装饰器，确保用户已认证
    def get(self, current_user):
        # 输出 current_user 调试信息
        print(f"current_user: {current_user}, type: {type(current_user)}")

        # 确保 current_user 是字典类型并包含 'username' 键
        if not isinstance(current_user, dict):
            return {"message": "Invalid user data"}, 400
        return {"message": f"Hello, {current_user['username']}!"}, 200
