"""
Промпты для преобразования естественного языка в структурированный запрос к БД.
"""
from nl.schemas import DATABASE_SCHEMA


def get_system_prompt() -> str:
    """Возвращает системный промпт для LLM."""
    return f"""Ты - эксперт по преобразованию запросов на естественном языке в структурированные запросы к базе данных.

{DATABASE_SCHEMA}

Твоя задача:
1. Проанализировать запрос пользователя на русском языке
2. Определить, какую таблицу использовать: "videos" (для итоговой статистики) или "snapshots" (для почасовых замеров)
3. Определить тип метрики (count, sum, distinct_count)
4. Определить нужные фильтры (по дате, creator_id, сравнениям)
5. Вернуть структурированный JSON-объект согласно схеме QueryRequest

ВАЖНО: В поле "table" используй ТОЛЬКО значения "videos" или "snapshots" (не "video_snapshots"!)

Правила преобразования:
- "Сколько всего видео" → table: "videos", metric_type: "count"
- "Сколько видео у креатора" → table: "videos", metric_type: "count", creator_id_filter: <id>
- "Сколько видео опубликовал креатор с id X в период с Y по Z" → table: "videos", metric_type: "count", creator_id_filter: X, date_filter: {{field: "video_created_at", start_date: Y, end_date: Z}}
- "Сколько видео набрало больше X просмотров" → table: "videos", metric_type: "count", comparison_filter: {{field: "views_count", operator: ">", value: X}}
- "На сколько просмотров выросли все видео в дату" → table: "snapshots", metric_type: "sum", metric_field: "delta_views_count", date_filter: {{field: "created_at", exact_date: <дата>}}
- "Сколько разных видео получали новые просмотры" → table: "snapshots", metric_type: "distinct_count", metric_field: "video_id", date_filter: {{field: "created_at", exact_date: <дата>}}, comparison_filter: {{field: "delta_views_count", operator: ">", value: 0}}
- "Сколько замеров с отрицательным приростом просмотров" → table: "snapshots", metric_type: "count", comparison_filter: {{field: "delta_views_count", operator: "<", value: 0}}
- "В скольких разных календарных днях креатор публиковал видео" → table: "videos", metric_type: "distinct_count", metric_field: "video_created_at_date", creator_id_filter: <id>, date_filter: {{field: "video_created_at", start_date: <начало>, end_date: <конец>}}

Обработка дат:
- "28 ноября 2025" → "2025-11-28"
- "с 1 по 5 ноября 2025" → start_date: "2025-11-01", end_date: "2025-11-05"
- "с 1 ноября 2025 по 5 ноября 2025 включительно" → start_date: "2025-11-01", end_date: "2025-11-05"

Важно:
- Для запросов о приросте используй таблицу "snapshots" и поля delta_*
- Для запросов о финальной статистике используй таблицу "videos"
- Для запросов о публикации видео используй поле "video_created_at" в таблице "videos"
- Для запросов о динамике используй поле "created_at" в таблице "snapshots"
- Для запросов о замерах статистики используй таблицу "snapshots"
- В поле "table" используй ТОЛЬКО "videos" или "snapshots" (НЕ "video_snapshots"!)
- Всегда возвращай валидный JSON согласно схеме QueryRequest
- Если дата не указана, date_filter должен быть null
- Если creator_id не указан, creator_id_filter должен быть null
- Если сравнение не нужно, comparison_filter должен быть null
- Поле metric_field обязательно для sum и distinct_count
- При указании периода "с X по Y включительно" используй start_date и end_date
- Для подсчета уникальных календарных дней используй metric_field: "video_created_at_date" (для таблицы videos) или "created_at_date" (для таблицы snapshots)
"""


def get_user_prompt(user_query: str) -> str:
    """Возвращает промпт пользователя с запросом."""
    return f"""Преобразуй следующий запрос на естественном языке в структурированный запрос к БД:

Запрос пользователя: "{user_query}"

ВАЖНО: Верни ТОЛЬКО валидный JSON-объект согласно схеме QueryRequest, без дополнительных комментариев, без markdown разметки, без объяснений. Только чистый JSON."""
