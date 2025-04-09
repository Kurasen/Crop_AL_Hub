from sqlalchemy import asc, desc


class QueryBuilder:
    @staticmethod
    def apply_sorting(query, params, model, allowed_fields):
        """统一处理排序逻辑"""
        if params.get('sort_by') in allowed_fields:
            order_func = desc if params.get('sort_order') == 'desc' else asc
            return query.order_by(order_func(getattr(model, params['sort_by'])), model.id.asc())
        return query

    @staticmethod
    def apply_pagination(query, params):
        """统一处理分页逻辑"""
        page = params.get('page', 1)
        per_page = params.get('per_page', 5)
        return query.offset((page - 1) * per_page).limit(per_page)


class BaseRepository:
    # 公共查询方法
    @staticmethod
    def base_search(query, params, model, allowed_sort_fields):
        """统一的基础查询流程"""
        # 处理排序
        query = QueryBuilder.apply_sorting(query, params, model, allowed_sort_fields)

        # 处理分页
        paginated_query = QueryBuilder.apply_pagination(query, params)

        # 返回总数和分页结果
        return query.count(), paginated_query.all()
