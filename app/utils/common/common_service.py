import re
from app.core.exception import logger, ValidationError
from typing import Set, Any


class CommonService:

    @staticmethod
    def get_all_types(repository: Any) -> list[str]:  # 接受 Repository 类或查询函数
        """获取所有唯一的类型标签"""
        try:
            # 从数据库获取所有模型的 type 字段
            all_type_strings = repository.get_all_type_strings()

            # 提取唯一类型
            unique_types: Set[str] = set()  # 显式类型注解
            for type_str in all_type_strings:
                # 处理可能的分隔符（中文；或英文;，避免空格干扰）
                types = re.split(r'[；;]', type_str)
                for t in types:
                    stripped_t: str = t.strip()  # 显式声明为 str
                    if stripped_t:
                        # 如果是必须使用 LiteralString 的场景
                        unique_types.add(stripped_t)

            # 排序后返回列表
            return sorted(unique_types)
        except Exception as e:
            logger.error(f"Error getting types: {str(e)}")
            raise e

    @staticmethod
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


