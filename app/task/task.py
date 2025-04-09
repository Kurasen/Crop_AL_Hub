from datetime import datetime

from sqlalchemy import JSON

from app.exts import db


class Task(db.Model):
    __tablename__ = 'task_table'
    __table_args__ = (
        db.CheckConstraint(
            "status IN ('PENDING', 'STARTED', 'SUCCESS', 'FAILURE', 'RETRY') OR status IS NULL",
            name='status_check'
        ),
        # 时间约束
        db.CheckConstraint(
            "created_at <= updated_at OR updated_at IS NULL",
            name='time_check'
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_table.id'), nullable=False, default=1)
    app_id = db.Column(db.Integer, db.ForeignKey('app_table.id'), nullable=False, default=1)
    models_ids = db.Column(JSON, nullable=True)  # 存储数组格式的JSON数据
    status = db.Column(db.String(20), nullable=True)
    remarks = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    result_info = db.Column(db.JSON, nullable=True)

    user = db.relationship("User", back_populates="tasks")
    app = db.relationship("App", back_populates="tasks")

    def __repr__(self):
        return f"<Task {self.name}>"

    def __init__(self, **kwargs):
        """
        :param kwargs: 数据集的各个字段参数
        """
        # 使用父类的初始化方法来处理字段初始化
        super().__init__(**kwargs)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "app_id": self.app_id,
            "app_name": self.app_name,
            "models_ids": self.models_ids,
            "image_path": self.image_path,
            "status": self.status,
            "remarks": self.remarks,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "result_info": self.result_info
        }