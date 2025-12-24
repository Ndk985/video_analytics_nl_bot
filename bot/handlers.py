import logging
from aiogram import Router
from aiogram.types import Message

from nl.parser import get_parser
from analytics.executor import QueryExecutor

logger = logging.getLogger(__name__)
router = Router()


@router.message()
async def handle_message(message: Message):
    """Обработчик текстовых сообщений от пользователя."""
    user_query = message.text

    if not user_query:
        await message.answer("Пожалуйста, отправьте текстовый запрос.")
        return

    try:
        logger.info(f"Обработка запроса от пользователя: {user_query}")

        # Получаем парсер
        parser = get_parser()

        # Преобразуем естественный язык в структурированный запрос
        query_request = await parser.parse_query(user_query)

        if not query_request:
            logger.warning(f"Не удалось распарсить запрос: {user_query}")
            await message.answer(
                "Не удалось обработать запрос. Пожалуйста, попробуйте переформулировать."
            )
            return

        logger.info(f"Запрос распарсен успешно: {query_request}")

        # Выполняем запрос к БД
        result = await QueryExecutor.execute_query(query_request)

        if result is None:
            await message.answer(
                "Произошла ошибка при выполнении запроса к базе данных."
            )
            return

        # Возвращаем результат - одно число
        await message.answer(str(result))

    except ValueError as e:
        # Ошибка инициализации парсера (например, нет API ключа)
        print(f"Ошибка инициализации: {e}")
        await message.answer(
            "Ошибка конфигурации бота. Обратитесь к администратору."
        )
    except Exception as e:
        print(f"Ошибка при обработке запроса: {e}")
        await message.answer(
            "Произошла ошибка при обработке вашего запроса. Попробуйте позже."
        )
