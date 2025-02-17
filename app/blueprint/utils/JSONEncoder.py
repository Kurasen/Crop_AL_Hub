# 自定义 JSONEncoder，处理 Decimal 类型
import json
from decimal import Decimal

from flask import Response


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)  # 将 Decimal 转换为 float
        return super().default(obj)


# 创建一个通用的 JSON 响应方法
def create_json_response(data, status_code=200):
    # 使用自定义 JSONEncoder 来序列化 JSON
    response = json.dumps(data, ensure_ascii=False, sort_keys=False, cls=CustomJSONEncoder)

    # 返回构建好的 Response 对象，设置正确的 content_type 和 HTTP 状态码
    return Response(response, content_type='application/json', status=status_code)
