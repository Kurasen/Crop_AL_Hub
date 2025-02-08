from app.exts import db


# 定义数据库模型
class Model(db.Model):
    __tablename__ = 'model_table'

    id = db.Column(db.Integer, primary_key=True)  # 主键
    name = db.Column(db.String(100), nullable=False)  # 模型名称
    image = db.Column(db.String(255), nullable=False)  # 模型图片路径
    input = db.Column(db.String(100), nullable=False)  # 输入类型
    description = db.Column(db.String(255))  # 描述
    cuda = db.Column(db.Boolean, default=False)  # 是否支持 CUDA
    instruction = db.Column(db.Text)  # 使用说明

    def __init__(self, name, image, input, description=None, cuda=False, instruction=None):
        self.name = name
        self.image = image
        self.input = input
        self.description = description
        self.cuda = cuda
        self.instruction = instruction

    def __repr__(self):
        return f'<Model {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'image': self.image,
            'input': self.input,
            'description': self.description,
            'cuda': bool(self.cuda),
            'instruction': self.instruction,
        }
