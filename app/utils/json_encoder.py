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
    """
    创建标准的 JSON 响应
    :param data: 响应的数据内容（可以是字典、列表等）
    :param status_code: HTTP 状态码，默认是 200
    :return: Flask Response 对象
    """
    # 如果 data 是字典，则保证返回 {"message": ...} 结构
    if isinstance(data, str):  # 如果传入的是字符串
        response_data = {"message": data, "status_code": status_code}
    else:
        response_data = data  # 如果是字典或其他类型，直接返回
    # 使用自定义 JSONEncoder 来序列化 JSON
    response = json.dumps(response_data, ensure_ascii=False, sort_keys=False, cls=CustomJSONEncoder)

    # 返回构建好的 Response 对象，设置正确的 content_type 和 HTTP 状态码
    return Response(response, content_type='application/json', status=status_code)
