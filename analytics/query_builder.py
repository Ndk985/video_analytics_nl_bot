"""
Построитель SQL запросов из структурированных запросов.
"""
from datetime import date, datetime
from typing import Optional
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
        # Преобразуем enum в реальное имя таблицы в БД
        table_name_map = {
            "videos": "videos",
            "snapshots": "video_snapshots"
        }
        table_name = table_name_map[query.table.value]

        # Определяем WHERE часть
        where_parts = []
        params = []
        param_index = 1

        # Проверяем, нужен ли JOIN для фильтрации по creator_id в snapshots
        needs_join = query.creator_id_filter and table_name == "video_snapshots"

        # Определяем SELECT часть (для JOIN нужно указывать полное имя таблицы)
        select_table = table_name if needs_join else None
        select_part = QueryBuilder._build_select(query, select_table)

        # Определяем FROM часть (с JOIN если нужно)
        if needs_join:
            from_part = f"FROM {table_name} INNER JOIN videos ON {table_name}.video_id = videos.id"
        else:
            from_part = f"FROM {table_name}"

        # Фильтр по дате
        if query.date_filter:
            # Для JOIN нужно указывать полное имя таблицы
            date_field = f"{table_name}.{query.date_filter.field}" if needs_join else query.date_filter.field
            date_filter_with_table = type(query.date_filter)(
                field=date_field,
                start_date=query.date_filter.start_date,
                end_date=query.date_filter.end_date,
                exact_date=query.date_filter.exact_date
            )
            date_where, date_params, param_index = QueryBuilder._build_date_filter(
                date_filter_with_table, param_index
            )
            where_parts.append(date_where)
            params.extend(date_params)

        # Фильтр по creator_id
        if needs_join:
            # Для таблицы snapshots используем JOIN
            where_parts.append(f"videos.creator_id = ${param_index}")
            params.append(query.creator_id_filter)
            param_index += 1
        elif query.creator_id_filter:
            # Для таблицы videos фильтр по creator_id напрямую
            where_parts.append(f"creator_id = ${param_index}")
            params.append(query.creator_id_filter)
            param_index += 1

        # Фильтр сравнения
        if query.comparison_filter:
            # Для JOIN нужно указывать полное имя таблицы
            comp_field = query.comparison_filter.field.value
            if needs_join:
                comp_field = f"{table_name}.{comp_field}"
            comp_where, comp_params, param_index = QueryBuilder._build_comparison_filter(
                query.comparison_filter, param_index, comp_field
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
    def _build_select(query: QueryRequest, table_name: Optional[str] = None) -> str:
        """
        Строит SELECT часть запроса.
        
        Args:
            query: Запрос
            table_name: Имя таблицы (для JOIN нужно указывать полное имя)
        """
        metric_type = query.metric_type

        if metric_type == MetricType.COUNT:
            return "SELECT COUNT(*)"
        elif metric_type == MetricType.SUM:
            if not query.metric_field:
                raise ValueError("metric_field обязателен для SUM")
            field = query.metric_field.value
            # Для JOIN нужно указывать полное имя таблицы
            if table_name:
                field = f"{table_name}.{field}"
            return f"SELECT SUM({field})"
        elif metric_type == MetricType.DISTINCT_COUNT:
            if not query.metric_field:
                raise ValueError("metric_field обязателен для DISTINCT_COUNT")
            field = query.metric_field.value
            
            # Специальная обработка для подсчета уникальных дат
            if field == "video_created_at_date":
                field = "video_created_at"
                if table_name:
                    field = f"{table_name}.{field}"
                return f"SELECT COUNT(DISTINCT DATE({field}))"
            elif field == "created_at_date":
                field = "created_at"
                if table_name:
                    field = f"{table_name}.{field}"
                return f"SELECT COUNT(DISTINCT DATE({field}))"
            
            # Обычное поле
            # Для JOIN нужно указывать полное имя таблицы
            if table_name:
                field = f"{table_name}.{field}"
            return f"SELECT COUNT(DISTINCT {field})"
        else:
            raise ValueError(f"Неизвестный тип метрики: {metric_type}")

    @staticmethod
    def _parse_date_or_datetime(date_str: str):
        """
        Парсит строку даты/времени в объект date или datetime.
        
        Args:
            date_str: Строка даты в формате YYYY-MM-DD или YYYY-MM-DDTHH:MM:SS
            
        Returns:
            Объект date или datetime
        """
        if isinstance(date_str, (date, datetime)):
            return date_str
        
        try:
            # Пробуем парсить как datetime (с временем)
            if 'T' in date_str or ' ' in date_str:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                # Только дата
                return date.fromisoformat(date_str)
        except ValueError:
            # Если не получилось, пробуем разные форматы
            for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            raise ValueError(f"Не удалось распарсить дату: {date_str}")

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
            # Точная дата
            date_obj = QueryBuilder._parse_date_or_datetime(date_filter.exact_date)
            if isinstance(date_obj, datetime):
                # Если есть время, используем прямое сравнение (точное время)
                where = f"{field} >= ${param_index} AND {field} < ${param_index + 1}"
                # Добавляем начало и конец дня для точной даты
                start_dt = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
                end_dt = start_dt.replace(day=start_dt.day + 1)
                params.extend([start_dt, end_dt])
                param_index += 2
            else:
                # Только дата, используем DATE()
                where = f"DATE({field}) = ${param_index}"
                params.append(date_obj)
                param_index += 1
        elif date_filter.start_date and date_filter.end_date:
            # Диапазон дат/времени
            start_obj = QueryBuilder._parse_date_or_datetime(date_filter.start_date)
            end_obj = QueryBuilder._parse_date_or_datetime(date_filter.end_date)
            
            # Если хотя бы одна дата содержит время, используем прямое сравнение
            if isinstance(start_obj, datetime) or isinstance(end_obj, datetime):
                # Преобразуем date в datetime для единообразия
                if isinstance(start_obj, date) and not isinstance(start_obj, datetime):
                    start_obj = datetime.combine(start_obj, datetime.min.time())
                if isinstance(end_obj, date) and not isinstance(end_obj, datetime):
                    # Для конечной даты добавляем конец дня, если время не указано
                    end_obj = datetime.combine(end_obj, datetime.max.time())
                
                where = f"{field} >= ${param_index} AND {field} <= ${param_index + 1}"
                params.extend([start_obj, end_obj])
                param_index += 2
            else:
                # Только даты, используем DATE()
                where = f"DATE({field}) >= ${param_index} AND DATE({field}) <= ${param_index + 1}"
                params.extend([start_obj, end_obj])
                param_index += 2
        elif date_filter.start_date:
            # Только начальная дата
            date_obj = QueryBuilder._parse_date_or_datetime(date_filter.start_date)
            if isinstance(date_obj, datetime):
                where = f"{field} >= ${param_index}"
            else:
                where = f"DATE({field}) >= ${param_index}"
            params.append(date_obj)
            param_index += 1
        elif date_filter.end_date:
            # Только конечная дата
            date_obj = QueryBuilder._parse_date_or_datetime(date_filter.end_date)
            if isinstance(date_obj, datetime):
                # Для datetime с временем используем <=, для конца дня добавляем время
                if isinstance(date_obj, datetime) and date_obj.hour == 0 and date_obj.minute == 0:
                    date_obj = date_obj.replace(hour=23, minute=59, second=59)
                where = f"{field} <= ${param_index}"
            else:
                where = f"DATE({field}) <= ${param_index}"
            params.append(date_obj)
            param_index += 1
        else:
            raise ValueError("date_filter должен содержать хотя бы одну дату")

        return where, params, param_index

    @staticmethod
    def _build_comparison_filter(comparison_filter, param_index: int, field_override: Optional[str] = None) -> tuple[str, list, int]:
        """
        Строит WHERE условие для фильтра сравнения.

        Args:
            comparison_filter: Фильтр сравнения
            param_index: Индекс параметра
            field_override: Переопределение поля (для JOIN)

        Returns:
            (WHERE условие, список параметров, новый param_index)
        """
        field = field_override if field_override else comparison_filter.field.value
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
