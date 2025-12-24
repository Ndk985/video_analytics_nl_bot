"""
Модуль для преобразования естественного языка в структурированные запросы к БД.
Использует DeepSeek API через OpenAI SDK.
"""
import json
import logging
from typing import Optional
from openai import AsyncOpenAI
from pydantic import ValidationError

from bot.config import DEEPSEEK_API_KEY, LLM_BASE_URL, LLM_MODEL
from nl.schemas import QueryRequest
from nl.prompt import get_system_prompt, get_user_prompt

logger = logging.getLogger(__name__)


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
        content = None
        json_data = None
        try:
            logger.info(f"Парсинг запроса: {user_query}")
            
            # Пробуем с response_format, если не поддерживается - уберем
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": get_user_prompt(user_query)}
                    ],
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )
            except Exception as format_error:
                logger.warning(f"response_format не поддерживается, пробуем без него: {format_error}")
                # Если response_format не поддерживается, пробуем без него
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": get_user_prompt(user_query)}
                    ],
                    temperature=0.1
                )

            content = response.choices[0].message.content
            logger.info(f"Ответ от LLM: {content}")
            
            if not content:
                logger.error("Пустой ответ от LLM")
                return None

            # Парсим JSON ответ
            json_data = json.loads(content)
            logger.info(f"Распарсенный JSON: {json_data}")

            # Валидируем через Pydantic
            query_request = QueryRequest(**json_data)
            logger.info(f"Валидация успешна: {query_request}")
            return query_request

        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON от LLM: {e}")
            logger.error(f"Ответ LLM: {content}")
            return None
        except ValidationError as e:
            logger.error(f"Ошибка валидации QueryRequest: {e}")
            logger.error(f"JSON от LLM: {json_data}")
            return None
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            
            # Специальная обработка ошибок API
            if "APIStatusError" in error_type or "402" in error_msg or "Insufficient Balance" in error_msg:
                logger.error(f"Недостаточно баланса на DeepSeek API: {error_msg}")
                logger.error("Пожалуйста, пополните баланс на https://platform.deepseek.com")
            elif "401" in error_msg or "Invalid API Key" in error_msg or "Unauthorized" in error_msg:
                logger.error(f"Неверный API ключ DeepSeek: {error_msg}")
            elif "429" in error_msg or "Rate limit" in error_msg:
                logger.error(f"Превышен лимит запросов к DeepSeek API: {error_msg}")
            else:
                logger.error(f"Ошибка при обращении к LLM API: {error_type}: {error_msg}")
                import traceback
                logger.error(traceback.format_exc())
            
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
