from functools import wraps
from flask import request

from app.utils import create_json_response


def require_json(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        data = request.get_json()
        if not data:
            return create_json_response("Request must be JSON", 400)
        return f(*args, **kwargs)

    return decorated_function
