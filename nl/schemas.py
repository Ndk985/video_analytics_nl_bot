"""
Схемы данных для преобразования естественного языка в структурированные запросы.
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class TableType(str, Enum):
    """Тип таблицы для запроса."""
    VIDEOS = "videos"
    SNAPSHOTS = "snapshots"


class MetricType(str, Enum):
    """Тип метрики для подсчета."""
    COUNT = "count"  # Подсчет количества записей
    SUM = "sum"  # Сумма значений
    DISTINCT_COUNT = "distinct_count"  # Количество уникальных значений


class MetricField(str, Enum):
    """Поле метрики."""
    VIEWS = "views_count"
    LIKES = "likes_count"
    COMMENTS = "comments_count"
    REPORTS = "reports_count"
    DELTA_VIEWS = "delta_views_count"
    DELTA_LIKES = "delta_likes_count"
    DELTA_COMMENTS = "delta_comments_count"
    DELTA_REPORTS = "delta_reports_count"
    VIDEO_ID = "video_id"
    CREATOR_ID = "creator_id"
    # Специальные значения для подсчета уникальных дат
    VIDEO_CREATED_AT_DATE = "video_created_at_date"  # Для COUNT(DISTINCT DATE(video_created_at))
    CREATED_AT_DATE = "created_at_date"  # Для COUNT(DISTINCT DATE(created_at))


class DateFilter(BaseModel):
    """Фильтр по дате."""
    field: str = Field(description="Поле для фильтрации (video_created_at или created_at)")
    start_date: Optional[str] = Field(None, description="Начальная дата в формате YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="Конечная дата в формате YYYY-MM-DD")
    exact_date: Optional[str] = Field(None, description="Точная дата в формате YYYY-MM-DD")


class ComparisonFilter(BaseModel):
    """Фильтр сравнения."""
    field: MetricField = Field(description="Поле для сравнения")
    operator: str = Field(description="Оператор: >, <, >=, <=, =")
    value: int = Field(description="Значение для сравнения")


class QueryRequest(BaseModel):
    """Структурированный запрос к базе данных."""
    table: TableType = Field(description="Таблица для запроса: videos или snapshots")
    metric_type: MetricType = Field(description="Тип метрики: count, sum, distinct_count")
    metric_field: Optional[MetricField] = Field(None, description="Поле метрики (если нужна сумма или distinct_count)")

    # Фильтры
    date_filter: Optional[DateFilter] = Field(None, description="Фильтр по дате")
    creator_id_filter: Optional[str] = Field(None, description="Фильтр по creator_id")
    comparison_filter: Optional[ComparisonFilter] = Field(None, description="Фильтр сравнения (например, views_count > 100000)")

    # Для запросов по приросту (delta)
    use_delta: bool = Field(False, description="Использовать приращения (delta_*) вместо абсолютных значений")

    class Config:
        json_schema_extra = {
            "example": {
                "table": "videos",
                "metric_type": "count",
                "date_filter": {
                    "field": "video_created_at",
                    "start_date": "2025-11-01",
                    "end_date": "2025-11-05"
                },
                "creator_id_filter": "aca1061a9d324ecf8c3fa2bb32d7be63"
            }
        }


# Описание схемы БД для промпта
DATABASE_SCHEMA = """
База данных содержит две таблицы:

1. Таблица `videos` (итоговая статистика по видео):
   - id (UUID) - идентификатор видео
   - creator_id (TEXT) - идентификатор креатора
   - video_created_at (TIMESTAMPTZ) - дата и время публикации видео
   - views_count (INTEGER) - финальное количество просмотров
   - likes_count (INTEGER) - финальное количество лайков
   - comments_count (INTEGER) - финальное количество комментариев
   - reports_count (INTEGER) - финальное количество жалоб
   - created_at (TIMESTAMPTZ) - служебное поле
   - updated_at (TIMESTAMPTZ) - служебное поле

2. Таблица `video_snapshots` (почасовые замеры статистики):
   - id (UUID) - идентификатор снапшота
   - video_id (UUID) - ссылка на видео (FK к videos.id)
   - views_count (INTEGER) - текущее количество просмотров на момент замера
   - likes_count (INTEGER) - текущее количество лайков на момент замера
   - comments_count (INTEGER) - текущее количество комментариев на момент замера
   - reports_count (INTEGER) - текущее количество жалоб на момент замера
   - delta_views_count (INTEGER) - приращение просмотров с прошлого замера
   - delta_likes_count (INTEGER) - приращение лайков с прошлого замера
   - delta_comments_count (INTEGER) - приращение комментариев с прошлого замера
   - delta_reports_count (INTEGER) - приращение жалоб с прошлого замера
   - created_at (TIMESTAMPTZ) - время замера (раз в час)
   - updated_at (TIMESTAMPTZ) - служебное поле

Важные моменты:
- Для запросов о приросте (например, "на сколько выросли просмотры") используйте таблицу snapshots и поля delta_*
- Для запросов о финальной статистике используйте таблицу videos
- Для запросов о динамике в конкретную дату используйте таблицу snapshots и фильтр по created_at
- Для запросов о количестве разных видео используйте DISTINCT video_id в таблице snapshots
"""
