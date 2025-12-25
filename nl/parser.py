"""
Модуль для преобразования естественного языка в структурированные запросы к БД.
Поддерживает разные LLM провайдеры через OpenAI-совместимый API:
- Ollama (локально)
- DeepSeek API
- OpenAI API
- Другие OpenAI-совместимые API
"""
import json
import logging
from typing import Optional
from openai import AsyncOpenAI
from pydantic import ValidationError

from bot.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_PROVIDER
from nl.schemas import QueryRequest
from nl.prompt import get_system_prompt, get_user_prompt

logger = logging.getLogger(__name__)


class NLParser:
    """Парсер естественного языка для преобразования запросов в структурированный формат."""

    def __init__(self, api_key: str, base_url: str, model: str, provider: str = "ollama"):
        """
        Инициализация парсера.

        Args:
            api_key: API ключ (для Ollama можно любой, например "ollama")
            base_url: Базовый URL API
            model: Модель для использования
            provider: Провайдер ("ollama", "deepseek", "openai" и т.д.)
        """
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model = model
        self.provider = provider
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
            
            # Для Ollama и некоторых других провайдеров response_format может не поддерживаться
            # Пробуем с response_format, если не поддерживается - уберем
            use_json_format = self.provider not in ["ollama"]  # Ollama может не поддерживать
            
            try:
                if use_json_format:
                    response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": self.system_prompt},
                            {"role": "user", "content": get_user_prompt(user_query)}
                        ],
                        temperature=0.1,
                        response_format={"type": "json_object"}
                    )
                else:
                    # Для Ollama пробуем без response_format, но просим JSON в промпте
                    response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": self.system_prompt},
                            {"role": "user", "content": get_user_prompt(user_query)}
                        ],
                        temperature=0.1
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

            # Очищаем ответ от markdown разметки (для Ollama и других моделей)
            content_clean = content.strip()
            # Убираем markdown блоки ```json ... ```
            if content_clean.startswith("```"):
                # Находим начало и конец JSON
                start = content_clean.find("{")
                end = content_clean.rfind("}") + 1
                if start != -1 and end > start:
                    content_clean = content_clean[start:end]
                else:
                    # Если не нашли, пробуем убрать только обратные кавычки
                    content_clean = content_clean.replace("```json", "").replace("```", "").strip()
            
            # Парсим JSON ответ
            json_data = json.loads(content_clean)
            logger.info(f"Распарсенный JSON: {json_data}")

            # Валидируем через Pydantic
            query_request = QueryRequest(**json_data)
            logger.info(f"Валидация успешна: table={query_request.table.value}, metric_type={query_request.metric_type.value}, "
                       f"creator_id_filter={query_request.creator_id_filter}, "
                       f"date_filter={query_request.date_filter}")
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
        if not LLM_API_KEY and LLM_PROVIDER != "ollama":
            raise ValueError(
                f"LLM_API_KEY не установлен для провайдера {LLM_PROVIDER}. "
                f"Установите переменную окружения или используйте LLM_PROVIDER=ollama"
            )
        
        # Для Ollama ключ не обязателен, но SDK требует его наличие
        api_key = LLM_API_KEY if LLM_API_KEY else "ollama"
        
        logger.info(
            f"Инициализация парсера: провайдер={LLM_PROVIDER}, "
            f"модель={LLM_MODEL}, base_url={LLM_BASE_URL}"
        )
        
        _parser = NLParser(
            api_key=api_key,
            base_url=LLM_BASE_URL,
            model=LLM_MODEL,
            provider=LLM_PROVIDER
        )
    return _parser
