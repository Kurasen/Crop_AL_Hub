from app.exts import db


# 定义数据库模型
class Model(db.Model):
    __tablename__ = 'model_table'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # 主键
    name = db.Column(db.String(100), nullable=False)  # 模型名称
    image = db.Column(db.String(255), nullable=False)  # 模型图片路径，长度改为 255
    input = db.Column(db.String(100), nullable=False)  # 输入类型
    description = db.Column(db.Text)  # 描述字段改为 Text 类型
    cuda = db.Column(db.Boolean, default=False)  # 是否支持 CUDA，默认 False
    instruction = db.Column(db.Text)
    output = db.Column(db.String(100))  # 输出字段
    accuracy = db.Column(db.Numeric(4, 2))  # 精度字段，DECIMAL(4, 2) 对应 Numeric(4, 2)
    type = db.Column(db.String(100))  # 模型类型
    sales = db.Column(db.Integer)  # 销售字段
    stars = db.Column(db.Integer)  # 收藏字段
    likes = db.Column(db.Integer)  # 点赞数字段

    def __init__(self, name, image, input, description=None, cuda=False, instruction=None, output=None, accuracy=None,
                 type=None, sales=None, stars=None, likes=None):
        self.name = name
        self.image = image
        self.input = input
        self.description = description
        self.cuda = cuda
        self.instruction = instruction
        self.output = output
        self.accuracy = accuracy
        self.type = type
        self.sales = sales
        self.stars = stars
        self.likes = likes

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
            'output': self.output,
            'accuracy': self.accuracy,
            'type': self.type,
            'sales': self.sales,
            'stars': self.stars,
            'likes': self.likes
        }
