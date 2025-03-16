# 自定义 JSONEncoder，处理 Decimal 类型
import json
import uuid
from decimal import Decimal

from flask import Response


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)  # 将 Decimal 转换为 float
        return super().default(obj)


def create_json_response(data, status=200):
    """
    创建标准的 JSON 响应
    :param status:
    :param data: 响应的数据内容（可以是字典、列表等）
    :return: Flask Response 对象
    """
    if isinstance(data, dict) and "error" in data:
        # 如果是错误响应，格式化成 message 和 status_code
        error_details = data["error"].get("details", {})
        error_message = data["error"].get("message", "")



        # 合并所有错误详情到 message 中
        if error_details:
            # 将错误详情内容合并为一个易于前端处理的字符串
            # error_message += " " + " ".join(f"{key}: {', '.join(errors)}" for key, errors in error_details.items())

            response_data = {
                "data": None,
                "msg":  error_message or "success",
                "errorDetails": [
                    {"field": field, "message": ', '.join(messages)}
                    for field, messages in error_details.items()
                ],  # 提取每个字段的错误消息并格式化
                "requestId": str(uuid.uuid4()),
                "code": status
            }
        else:
            response_data = {
                "data": None,
                "message":  error_message or "success",
                "requestId": str(uuid.uuid4()),
                "status_code": status
            }

    else:
        # 正常响应，保持原样
        response_data = {
            "data": data.get("data"),  # 直接提取data字段
            "message": data.get("message") or "success",
            "requestId": str(uuid.uuid4()),
            "status_code": status
        }

    # 使用自定义 JSONEncoder 来序列化 JSON
    response = json.dumps(response_data, ensure_ascii=False, sort_keys=False, cls=CustomJSONEncoder)

    # 返回构建好的 Response 对象，设置正确的 content_type 和 HTTP 状态码
    return Response(response, content_type='application/json', status=status)
