from app.core.exception import ValidationError


def apply_sorting(query, params, model, valid_sort_fields):
    """
    通用的查询排序方法

    :param query:           数据库查询对象
    :param params:          请求参数字典
    :param model:           数据库模型类
    :param valid_sort_fields: 允许排序的字段列表
    :return:                处理后的查询对象
    """
    sort_by = params.get('sort_by')
    sort_order = params.get('sort_order')

    # 验证排序参数有效性
    if sort_by:
        if sort_by not in valid_sort_fields:
            raise ValidationError(
                f"Invalid sort field. Allowed fields: {valid_sort_fields}"
            )

        # 获取排序字段并构造排序条件
        sort_field = getattr(model, sort_by)
        if sort_order == 'desc':
            query = query.order_by(sort_field.desc(), model.id.asc())
        else:
            query = query.order_by(sort_field.asc(), model.id.asc())

    # 处理没有 sort_by 但有 sort_order 的非法情况
    elif not sort_by and sort_order:
        raise ValidationError("Sort order requires sort_by parameter")

    return query
