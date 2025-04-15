import json
import uuid
from decimal import Decimal

from flask import Response


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)  # 将 Decimal 转换为 float
        return super().default(obj)


def create_json_response(data=None, status=200, http_status=200):
    """
    创建标准的 JSON 响应
    :param http_status:默认返回200
    :param status:
    :param data: 响应的数据内容（可以是字典、列表等）
    :return: Flask Response 对象
    """
    # if status == 204:  # 204 No Content
    #     response_data = {"msg": "success", "requestId": str(uuid.uuid4()), "code": status,}
    if isinstance(data, dict) and "error" in data:
        # 如果是错误响应，格式化成 message 和 status_code
        error_details = data["error"].get("details", {})
        error_message = data["error"].get("message", "")

        if error_details:
            response_data = {
                "data": None,
                "msg": error_message or "fail",
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
                "msg": error_message or "success",
                "requestId": str(uuid.uuid4()),
                "code": status
            }

    else:
        # 正常响应，保持原样
        response_data = {
            "data": data.get("data") if data else None,
            "msg": data.get("message") or "success",
            "requestId": str(uuid.uuid4()),
            "code": status
        }

    print(response_data)
    # 使用自定义 JSONEncoder 来序列化 JSON
    response = json.dumps(response_data, ensure_ascii=False, sort_keys=False, cls=CustomJSONEncoder)

    # 返回构建好的 Response 对象，设置正确的 content_type 和 HTTP 状态码
    return Response(response, content_type='application/json', status=http_status)


class ResponseBuilder:
    @staticmethod
    def paginated_response(items, total_count, page, per_page):
        """更健壮的分页响应"""
        return {
            "data": {
                "items": items or [],  # 保证空列表而非None
                "total": total_count,
                "page": page,
                "per_page": per_page,
                "total_pages": max(1, (total_count + per_page - 1) // per_page),
                "has_next": (page * per_page) < total_count,
                "has_prev": page > 1
            }
        }