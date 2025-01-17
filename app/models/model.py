from app.exts import db

# 定义数据库模型
class Model(db.Model):
    __tablename__ = 'model_table'

    id = db.Column(db.Integer, primary_key=True)  # 主键
    name = db.Column(db.String(100), nullable=False)  # 模型名称
    image = db.Column(db.String(255), nullable=False)  # 模型图片路径
    input = db.Column(db.String(100), nullable=False)  # 输入类型
    describe = db.Column(db.String(255))  # 描述
    cuda = db.Column(db.Boolean, default=False)  # 是否支持 CUDA
    instruction = db.Column(db.Text)  # 使用说明

    def __init__(self, name, image, input, describe=None, cuda=False, instruction=None):
        self.name = name
        self.image = image
        self.input = input
        self.describe = describe
        self.cuda = cuda
        self.instruction = instruction

    def __repr__(self):
        return f'<Model {self.name}>'

# 模型查询函数：获取所有模型
def get_all_models():
    return Model.query.all()