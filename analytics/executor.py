"""
Исполнитель SQL запросов к базе данных.
"""
from typing import Optional

from db.database import get_pool
from analytics.query_builder import QueryBuilder
from nl.schemas import QueryRequest


class QueryExecutor:
    """Исполнитель запросов к базе данных."""

    @staticmethod
    async def execute_query(query: QueryRequest) -> Optional[int]:
        """
        Выполняет структурированный запрос и возвращает результат.

        Args:
            query: Структурированный запрос

        Returns:
            Числовой результат или None в случае ошибки
        """
        sql = None
        params = None
        try:
            # Строим SQL запрос
            sql, params = QueryBuilder.build_sql(query)

            # Получаем пул соединений
            pool = await get_pool()

            # Выполняем запрос
            async with pool.acquire() as conn:
                result = await conn.fetchval(sql, *params)

                # Преобразуем результат в int (может быть None, Decimal и т.д.)
                if result is None:
                    return 0

                return int(result)

        except Exception as e:
            print(f"Ошибка при выполнении SQL запроса: {e}")
            if sql:
                print(f"SQL: {sql}")
            if params:
                print(f"Params: {params}")
            return None
