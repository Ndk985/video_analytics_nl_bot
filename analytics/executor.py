"""
Исполнитель SQL запросов к базе данных.
"""
import logging
from typing import Optional

from db.database import get_pool
from analytics.query_builder import QueryBuilder
from nl.schemas import QueryRequest

logger = logging.getLogger(__name__)


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
            logger.debug(f"Сгенерированный SQL: {sql}")
            logger.debug(f"Параметры SQL: {params}")

            # Получаем пул соединений
            pool = await get_pool()

            # Выполняем запрос
            async with pool.acquire() as conn:
                result = await conn.fetchval(sql, *params)
                logger.debug(f"Результат запроса: {result}")

                # Преобразуем результат в int (может быть None, Decimal и т.д.)
                if result is None:
                    return 0

                return int(result)

        except Exception as e:
            logger.error(f"Ошибка при выполнении SQL запроса: {e}")
            if sql:
                logger.debug(f"SQL: {sql}")
            if params:
                logger.debug(f"Params: {params}")
            import traceback
            logger.debug(traceback.format_exc())
            return None
