from flask import Flask
from flask_restx import Api, Resource

app = Flask(__name__)
api = Api(app)

# 创建简单的 DatasetSearchResource 以测试
class DatasetSearchResource(Resource):
    def get(self):
        return {"message": "Search is working!"}

# 添加路由
api.add_resource(DatasetSearchResource, '/datasets/search')

if __name__ == '__main__':
    app.run(debug=True)