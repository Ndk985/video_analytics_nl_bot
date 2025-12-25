"""
Построитель SQL запросов из структурированных запросов.
"""
from datetime import date
from nl.schemas import QueryRequest, MetricType


class QueryBuilder:
    """Построитель SQL запросов."""

    @staticmethod
    def build_sql(query: QueryRequest) -> tuple[str, list]:
        """
        Строит SQL запрос на основе QueryRequest.

        Args:
            query: Структурированный запрос

        Returns:
            Кортеж (SQL запрос, список параметров)
        """
        table_name = query.table.value

        # Определяем SELECT часть
        select_part = QueryBuilder._build_select(query)

        # Определяем FROM часть
        from_part = f"FROM {table_name}"

        # Определяем WHERE часть
        where_parts = []
        params = []
        param_index = 1

        # Фильтр по дате
        if query.date_filter:
            date_where, date_params, param_index = QueryBuilder._build_date_filter(
                query.date_filter, param_index
            )
            where_parts.append(date_where)
            params.extend(date_params)

        # Фильтр по creator_id
        if query.creator_id_filter:
            where_parts.append(f"creator_id = ${param_index}")
            params.append(query.creator_id_filter)
            param_index += 1

        # Фильтр сравнения
        if query.comparison_filter:
            comp_where, comp_params, param_index = QueryBuilder._build_comparison_filter(
                query.comparison_filter, param_index
            )
            where_parts.append(comp_where)
            params.extend(comp_params)

        # Собираем WHERE
        where_part = ""
        if where_parts:
            where_part = "WHERE " + " AND ".join(where_parts)

        # Собираем полный запрос
        sql = f"{select_part}\n{from_part}\n{where_part}"

        return sql, params

    @staticmethod
    def _build_select(query: QueryRequest) -> str:
        """Строит SELECT часть запроса."""
        metric_type = query.metric_type

        if metric_type == MetricType.COUNT:
            return "SELECT COUNT(*)"
        elif metric_type == MetricType.SUM:
            if not query.metric_field:
                raise ValueError("metric_field обязателен для SUM")
            field = query.metric_field.value
            return f"SELECT SUM({field})"
        elif metric_type == MetricType.DISTINCT_COUNT:
            if not query.metric_field:
                raise ValueError("metric_field обязателен для DISTINCT_COUNT")
            field = query.metric_field.value
            return f"SELECT COUNT(DISTINCT {field})"
        else:
            raise ValueError(f"Неизвестный тип метрики: {metric_type}")

    @staticmethod
    def _build_date_filter(date_filter, param_index: int) -> tuple[str, list, int]:
        """
        Строит WHERE условие для фильтра по дате.

        Returns:
            (WHERE условие, список параметров, новый param_index)
        """
        field = date_filter.field
        params = []

        if date_filter.exact_date:
            # Точная дата - используем DATE() для сравнения
            where = f"DATE({field}) = ${param_index}"
            # Преобразуем строку в объект date для asyncpg
            date_obj = date.fromisoformat(date_filter.exact_date) if isinstance(date_filter.exact_date, str) else date_filter.exact_date
            params.append(date_obj)
            param_index += 1
        elif date_filter.start_date and date_filter.end_date:
            # Диапазон дат
            where = f"DATE({field}) >= ${param_index} AND DATE({field}) <= ${param_index + 1}"
            # Преобразуем строки в объекты date для asyncpg
            start_date_obj = date.fromisoformat(date_filter.start_date) if isinstance(date_filter.start_date, str) else date_filter.start_date
            end_date_obj = date.fromisoformat(date_filter.end_date) if isinstance(date_filter.end_date, str) else date_filter.end_date
            params.extend([start_date_obj, end_date_obj])
            param_index += 2
        elif date_filter.start_date:
            # Только начальная дата
            where = f"DATE({field}) >= ${param_index}"
            date_obj = date.fromisoformat(date_filter.start_date) if isinstance(date_filter.start_date, str) else date_filter.start_date
            params.append(date_obj)
            param_index += 1
        elif date_filter.end_date:
            # Только конечная дата
            where = f"DATE({field}) <= ${param_index}"
            date_obj = date.fromisoformat(date_filter.end_date) if isinstance(date_filter.end_date, str) else date_filter.end_date
            params.append(date_obj)
            param_index += 1
        else:
            raise ValueError("date_filter должен содержать хотя бы одну дату")

        return where, params, param_index

    @staticmethod
    def _build_comparison_filter(comparison_filter, param_index: int) -> tuple[str, list, int]:
        """
        Строит WHERE условие для фильтра сравнения.

        Returns:
            (WHERE условие, список параметров, новый param_index)
        """
        field = comparison_filter.field.value
        operator = comparison_filter.operator
        value = comparison_filter.value

        # Валидация оператора
        valid_operators = [">", "<", ">=", "<=", "=", "!="]
        if operator not in valid_operators:
            raise ValueError(f"Недопустимый оператор: {operator}")

        where = f"{field} {operator} ${param_index}"
        params = [value]
        param_index += 1

        return where, params, param_index
