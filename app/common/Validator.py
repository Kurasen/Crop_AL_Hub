from typing import Dict, Callable, List
from app.exception.errors import ValidationError


class Validator:
    """
    基础校验器，支持链式调用
    """

    def __init__(self):
        """
        初始化校验器实例

        初始化时会创建一个空的规则列表 `_rules` 和一个空的自定义错误消息字典 `_custom_errors`。
        """
        self._rules = []
        self._custom_errors = {}

    def required(self, fields: List[str], custom_messages: Dict[str, str] = None) -> 'Validator':
        """
        校验指定字段是否存在且不能为空

        :param fields: 需要校验的字段名列表
        :param custom_messages: 可选的自定义错误消息字典，键为字段名，值为错误消息
        :return: 返回当前 `Validator` 实例，支持链式调用
        """

        def check(data):
            """检查数据中是否包含必填字段且字段值不为空"""
            missing = []  # 存储缺失或为空的字段
            for f in fields:
                value = data.get(f)
                if value is None or (isinstance(value, str) and value.strip() == ""):
                    missing.append(f)

            if missing:
                resolved_messages = custom_messages or {}  # 处理 custom_messages 为 None 的情况
                messages = [resolved_messages.get(f, f"字段 {f} 不能为空") for f in missing]
                msg = "; ".join(messages)
                raise ValidationError(msg)
            return data

        self._rules.append(check)
        return self

    def type_check(self, field_type_map: Dict[str, type]) -> 'Validator':
        """
        校验字段类型是否匹配

        :param field_type_map: 字段与期望类型的映射字典
        :return: 返回当前 `Validator` 实例，支持链式调用
        """
        def check(data):
            """检查每个字段的类型是否符合要求"""
            errors = []
            for field, expected_type in field_type_map.items():
                if field in data:
                    if not isinstance(data[field], expected_type):
                        msg = self._custom_errors.get(f'type_{field}') or \
                              f"字段 '{field}' 类型错误，应为 {expected_type.__name__}"
                        errors.append(msg)
            if errors:
                raise ValidationError("; ".join(errors))

        self._rules.append(check)
        return self

    def regex_match(self, field_pattern_map: Dict[str, str], fullmatch=True) -> 'Validator':
        """
        校验字段值是否匹配指定的正则表达式

        :param field_pattern_map: 字段与正则表达式的映射字典
        :param fullmatch: 如果为 `True`，要求完全匹配；如果为 `False`，要求部分匹配
        :return: 返回当前 `Validator` 实例，支持链式调用
        """
        def check(data):
            """检查字段值是否匹配正则表达式"""
            import re
            errors = []
            for field, pattern in field_pattern_map.items():
                if field in data:
                    value = str(data[field])
                    if (fullmatch and not re.fullmatch(pattern, value)) or (
                            not fullmatch and not re.search(pattern, value)):
                        msg = self._custom_errors.get(f'regex_{field}') or \
                              f"字段 '{field}' 格式不符合要求"
                        errors.append(msg)
            if errors:
                raise ValidationError("; ".join(errors))

        self._rules.append(check)
        return self

    def custom(self, func: Callable[[Dict], None]) -> 'Validator':
        """
        添加自定义校验规则

        :param func: 自定义的校验函数，接受一个数据字典并在验证失败时抛出异常
        :return: 返回当前 `Validator` 实例，支持链式调用
        """
        if not callable(func):
            raise TypeError("The custom validation function must be callable.")
        self._rules.append(func)
        return self

    def error_messages(self, messages: Dict[str, str]) -> 'Validator':
        """
        设置自定义错误消息

        :param messages: 自定义错误消息字典，键为规则名称或字段名，值为对应的错误消息
        :return: 返回当前 `Validator` 实例，支持链式调用
        """
        self._custom_errors.update(messages)
        return self

    def validate(self, data: Dict) -> None:
        """
        执行所有注册的校验规则

        :param data: 待校验的数据字典
        :raises ValidationError: 如果有校验失败，会抛出 ValidationError
        """
        errors = {}
        for rule in self._rules:
            try:
                rule(data)
            except ValidationError as e:
                errors[rule.__name__] = str(e)

        if errors:
            error_messages = "；".join(errors.values())  # 将多个错误消息拼接
            raise ValidationError(error_messages)
