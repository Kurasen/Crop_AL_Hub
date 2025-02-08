from flask_restx import Api

# 定义 Swagger 认证信息
authorizations = {
    'BearerAuth': {
        'type': 'apiKey',
        'in': 'header',  # 认证信息在 Header 里
        'name': 'Authorization'  # 请求头字段名
    }
}


def configure_swagger(api: Api):
    """配置 Swagger 认证"""
    api.authorizations = authorizations
    api.security = [{'BearerAuth': []}]
