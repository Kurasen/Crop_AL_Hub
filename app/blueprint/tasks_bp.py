from flask import Blueprint

from app.utils import create_json_response

tasks_bp = Blueprint('tasks', __name__, url_prefix='/api/v1/tasks')



