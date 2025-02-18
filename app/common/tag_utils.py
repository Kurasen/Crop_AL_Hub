
import re
from app.exception.errors import ValidationError


def process_and_filter_tags(query, type_field, type_str):
    """
    处理并过滤标签，支持多个标签模糊查询
    :param query: 当前查询对象
    :param type_field: 用于匹配标签的字段（例如 Dataset.type 或 Model.type）
    :param type_str: 用户输入的 type 字符串
    :return: 返回处理后的查询对象
    """
    if type_str:
        # 检测非法字符（仅允许汉字、英文字母、数字、空格、逗号、分号）
        if re.search(r"[^\u4e00-\u9fa5a-zA-Z0-9,，; ；]", type_str):
            raise ValidationError("Invalid input. Only Chinese characters, English letters, numbers, spaces, commas, "
                                  "and semicolons are allowed.")

        # 使用正则表达式分割，支持逗号 `,`、分号 `;`、空格 ` ` 作为分隔符
        tags = re.split(r'[,\s;，；]+', type_str)
        tags = [tag.strip() for tag in tags if tag.strip()]  # 去除空格并过滤空标签

        # 遍历所有标签，确保查询的字段包含每个输入的标签
        for tag in tags:
            query = query.filter(type_field.ilike(f"%{tag}%"))

    return query
