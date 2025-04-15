from sqlalchemy import asc, desc
from sqlalchemy.orm import Query


class PaginationHelper:
    @staticmethod
    def paginate(
            query: Query,
            page: int = 1,
            per_page: int = 10,
            sort_mapping: dict = None,
            sort_by: str = None,
            sort_order: str = 'asc',
            max_per_page: int = 100
    ) -> tuple[int, list]:
        """
        通用分页排序方法

        :param query: SQLAlchemy查询对象
        :param page: 当前页码
        :param per_page: 每页数量
        :param sort_mapping: 排序字段映射 {前端参数: 模型字段}
        :param sort_by: 排序字段名
        :param sort_order: 排序方向(asc/desc)
        :param max_per_page: 最大每页数量限制
        :return: (总记录数, 当前页数据列表)
        """
        # 参数校验
        page = max(1, page)
        per_page = min(max_per_page, max(1, per_page))

        # 排序处理
        if sort_mapping and sort_by and sort_by in sort_mapping:
            sort_field = sort_mapping[sort_by]
            order_func = desc if sort_order == 'desc' else asc
            query = query.order_by(order_func(sort_field), asc(query.column_descriptions[0]['entity'].id))

        # 分页查询
        total_count = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()

        return total_count, items
