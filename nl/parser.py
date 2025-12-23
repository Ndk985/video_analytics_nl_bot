"""
Модуль для преобразования естественного языка в структурированные запросы к БД.
Использует DeepSeek API через OpenAI SDK.
"""
import json
from typing import Optional
from openai import AsyncOpenAI
from pydantic import ValidationError

from bot.config import DEEPSEEK_API_KEY, LLM_BASE_URL, LLM_MODEL
from nl.schemas import QueryRequest
from nl.prompt import get_system_prompt, get_user_prompt


class NLParser:
    """Парсер естественного языка для преобразования запросов в структурированный формат."""

    def __init__(self, api_key: str, base_url: str, model: str = "deepseek-chat"):
        """
        Инициализация парсера.

        Args:
            api_key: API ключ DeepSeek
            base_url: Базовый URL API (по умолчанию DeepSeek)
            model: Модель для использования (по умолчанию deepseek-chat)
        """
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model = model
        self.system_prompt = get_system_prompt()

    async def parse_query(self, user_query: str) -> Optional[QueryRequest]:
        """
        Преобразует запрос на естественном языке в структурированный QueryRequest.

        Args:
            user_query: Запрос пользователя на русском языке

        Returns:
            QueryRequest или None в случае ошибки
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": get_user_prompt(user_query)}
                ],
                temperature=0.1,  # Низкая температура для более детерминированных результатов
                response_format={"type": "json_object"}  # Требуем JSON ответ
            )

            content = response.choices[0].message.content
            if not content:
                return None

            # Парсим JSON ответ
            json_data = json.loads(content)

            # Валидируем через Pydantic
            query_request = QueryRequest(**json_data)
            return query_request

        except json.JSONDecodeError as e:
            print(f"Ошибка парсинга JSON от LLM: {e}")
            print(f"Ответ LLM: {content if 'content' in locals() else 'N/A'}")
            return None
        except ValidationError as e:
            print(f"Ошибка валидации QueryRequest: {e}")
            print(f"JSON от LLM: {json_data if 'json_data' in locals() else 'N/A'}")
            return None
        except Exception as e:
            print(f"Ошибка при обращении к LLM API: {e}")
            return None


# Глобальный экземпляр парсера (будет инициализирован при старте бота)
_parser: Optional[NLParser] = None


def get_parser() -> NLParser:
    """Возвращает глобальный экземпляр парсера."""
    global _parser
    if _parser is None:
        if not DEEPSEEK_API_KEY:
            raise ValueError("DEEPSEEK_API_KEY не установлен в переменных окружения")
        _parser = NLParser(
            api_key=DEEPSEEK_API_KEY,
            base_url=LLM_BASE_URL,
            model=LLM_MODEL
        )
    return _parser
