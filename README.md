# Telegram-бот для аналитики по видео на основе задач на естественном языке

Telegram-бот, который обрабатывает запросы на естественном языке и возвращает аналитические метрики по видео из базы данных PostgreSQL.

## Описание проекта

Бот принимает текстовые сообщения на русском языке, преобразует их в SQL-запросы с помощью LLM (DeepSeek API, OpenAI API или локальная Ollama) и возвращает пользователю числовой результат.

### Примеры запросов:
- "Сколько всего видео есть в системе?"
- "Сколько видео у креатора с id aca1061a9d324ecf8c3fa2bb32d7be63 вышло с 1 ноября 2025 по 5 ноября 2025 включительно?"
- "Сколько видео набрало больше 100000 просмотров за всё время?"
- "На сколько просмотров в сумме выросли все видео 28 ноября 2025?"
- "Сколько разных видео получали новые просмотры 27 ноября 2025?"

## Архитектура

Проект использует многоуровневую архитектуру для преобразования естественного языка в SQL-запросы:

### 1. Модуль обработки естественного языка (`nl/`)
- **`schemas.py`** - Pydantic-схемы для структурированного представления запросов:
  - `QueryRequest` - структурированный запрос с указанием таблицы, типа метрики, фильтров
  - Описание схемы БД для LLM
- **`prompt.py`** - промпты для LLM:
  - Системный промпт с описанием структуры БД и правил преобразования
  - Пользовательский промпт с запросом пользователя
- **`parser.py`** - модуль взаимодействия с LLM API:
  - Преобразует естественный язык в структурированный `QueryRequest`
  - Поддерживает DeepSeek API, OpenAI API и локальную Ollama

### 2. Модуль аналитики (`analytics/`)
- **`query_builder.py`** - построитель SQL-запросов:
  - Преобразует `QueryRequest` в SQL-запрос с параметрами
  - Обрабатывает фильтры по дате, creator_id, сравнениям
  - Поддерживает COUNT, SUM, DISTINCT COUNT
- **`executor.py`** - исполнитель SQL-запросов:
  - Выполняет SQL-запросы к PostgreSQL через asyncpg
  - Возвращает числовой результат

### 3. Модуль бота (`bot/`)
- **`main.py`** - точка входа, запуск бота через aiogram
- **`handlers.py`** - обработчик сообщений:
  - Принимает текстовый запрос от пользователя
  - Вызывает парсер для преобразования в структурированный запрос
  - Выполняет запрос через executor
  - Возвращает результат пользователю
- **`config.py`** - конфигурация (токены, URL БД, настройки LLM)

### 4. Модуль базы данных (`db/`)
- **`database.py`** - пул соединений с PostgreSQL
- **`schema.sql`** - схема БД (таблицы videos и video_snapshots)
- **`load_data.py`** - скрипт загрузки данных из JSON

### Подход к преобразованию текстовых запросов в SQL

1. **Парсинг естественного языка** (LLM):
   - LLM получает системный промпт с описанием структуры БД
   - Промпт содержит правила преобразования типичных запросов
   - LLM возвращает структурированный JSON согласно схеме `QueryRequest`

2. **Построение SQL** (детерминированный код):
   - `QueryBuilder` преобразует `QueryRequest` в SQL-запрос
   - Используются параметризованные запросы для безопасности
   - Обрабатываются все типы фильтров и метрик

3. **Выполнение запроса**:
   - Асинхронное выполнение через asyncpg
   - Возврат числового результата

**Почему такой подход?**
- LLM используется только для понимания естественного языка и структурирования запроса
- SQL генерируется детерминированным кодом, что исключает SQL-инъекции и ошибки синтаксиса
- Промпт содержит четкое описание схемы БД и примеры преобразований

## Требования

- Python 3.11.9
- PostgreSQL 15
- Docker и Docker Compose (рекомендуется)
- LLM провайдер: DeepSeek API, OpenAI API или локальная Ollama

## Установка и запуск

### 1. Клонирование репозитория

```bash
git clone <repository_url>
cd video_analytics_nl_bot
```

### 2. Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```env
# Telegram бот
BOT_TOKEN=your_telegram_bot_token

# База данных
DATABASE_URL=postgresql://postgres:postgres@db:5432/postgres

# LLM провайдер (ollama, deepseek, openai)
LLM_PROVIDER=deepseek

# Для DeepSeek API:
DEEPSEEK_API_KEY=your_deepseek_api_key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat

# Для OpenAI API:
# LLM_PROVIDER=openai
# OPENAI_API_KEY=your_openai_api_key
# LLM_BASE_URL=https://api.openai.com/v1
# LLM_MODEL=gpt-4o-mini

# Для локальной Ollama:
# LLM_PROVIDER=ollama
# LLM_BASE_URL=http://host.docker.internal:11434/v1
# LLM_MODEL=llama3.2
```

**Где взять токен бота:**
1. Откройте Telegram и найдите бота [@BotFather](https://t.me/BotFather)
2. Отправьте команду `/newbot` и следуйте инструкциям
3. Скопируйте полученный токен в `.env`

**Где взять API ключи:**
- **DeepSeek**: https://platform.deepseek.com/api_keys
- **OpenAI**: https://platform.openai.com/api-keys
- **Ollama**: не требует ключа (см. [OLLAMA_SETUP.md](OLLAMA_SETUP.md))

### 3. Запуск через Docker Compose

**Важно:** Перед запуском убедитесь, что вы скачали JSON-файл с данными по ссылке из ТЗ и поместили его в папку `data/` с именем `videos.json`.

```bash
# Запуск базы данных и бота
docker-compose up -d

# Загрузка данных в БД
docker-compose exec bot python -m db.load_data data/videos.json

# Просмотр логов
docker-compose logs -f bot
```

### 4. Запуск без Docker

#### 4.1. Установка зависимостей

```bash
pip install -r requirements.txt
```

#### 4.2. Запуск PostgreSQL

Убедитесь, что PostgreSQL запущен и доступен по адресу из `DATABASE_URL`.

#### 4.3. Создание таблиц

```bash
psql -U postgres -d postgres -f db/schema.sql
```

#### 4.4. Загрузка данных

```bash
python -m db.load_data data/videos.json
```

#### 4.5. Запуск бота

```bash
python -m bot.main
```

## Настройка LLM провайдера

### DeepSeek API (по умолчанию)

```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your-api-key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

### OpenAI API

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your-api-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

### Локальная Ollama

Подробная инструкция в [OLLAMA_SETUP.md](OLLAMA_SETUP.md)

```env
LLM_PROVIDER=ollama
LLM_BASE_URL=http://host.docker.internal:11434/v1
LLM_MODEL=llama3.2
```

## Структура базы данных

### Таблица `videos`
Итоговая статистика по каждому видео:
- `id` (UUID) - идентификатор видео
- `creator_id` (TEXT) - идентификатор креатора
- `video_created_at` (TIMESTAMPTZ) - дата и время публикации видео
- `views_count` (INTEGER) - финальное количество просмотров
- `likes_count` (INTEGER) - финальное количество лайков
- `comments_count` (INTEGER) - финальное количество комментариев
- `reports_count` (INTEGER) - финальное количество жалоб
- `created_at`, `updated_at` (TIMESTAMPTZ) - служебные поля

### Таблица `video_snapshots`
Почасовые замеры статистики по каждому видео:
- `id` (UUID) - идентификатор снапшота
- `video_id` (UUID) - ссылка на видео (FK)
- `views_count`, `likes_count`, `comments_count`, `reports_count` (INTEGER) - текущие значения на момент замера
- `delta_views_count`, `delta_likes_count`, `delta_comments_count`, `delta_reports_count` (INTEGER) - приращения с прошлого замера
- `created_at` (TIMESTAMPTZ) - время замера (раз в час)
- `updated_at` (TIMESTAMPTZ) - служебное поле

## Использование

1. Найдите вашего бота в Telegram по username, который вы указали при создании через @BotFather
2. Отправьте боту текстовый запрос на русском языке
3. Бот вернет числовой результат

Примеры запросов:
- "Сколько всего видео есть в системе?"
- "Сколько видео у креатора с id aca1061a9d324ecf8c3fa2bb32d7be63 вышло с 1 ноября 2025 по 5 ноября 2025 включительно?"
- "Сколько видео набрало больше 100000 просмотров за всё время?"
- "На сколько просмотров в сумме выросли все видео 28 ноября 2025?"
- "Сколько разных видео получали новые просмотры 27 ноября 2025?"

## Технологии

- **Python 3.11.9** - язык программирования
- **PostgreSQL 15** - база данных
- **aiogram 3.x** - фреймворк для Telegram-бота
- **asyncpg** - асинхронный драйвер PostgreSQL
- **OpenAI SDK** - для работы с LLM API (DeepSeek, OpenAI, Ollama)
- **Pydantic** - валидация данных
- **Docker & Docker Compose** - контейнеризация

## Особенности реализации

- Полностью асинхронный стек (aiogram, asyncpg, OpenAI SDK)
- Безопасность: параметризованные SQL-запросы
- Модульная архитектура для легкого тестирования и расширения
- Детерминированная генерация SQL (без галлюцинаций)
- Подробное описание схемы БД в промпте для LLM
- Поддержка нескольких LLM провайдеров с возможностью переключения
- Детальное логирование для отладки

## Структура проекта

```
video_analytics_nl_bot/
├── analytics/          # Модуль аналитики
│   ├── executor.py     # Исполнитель SQL-запросов
│   └── query_builder.py # Построитель SQL-запросов
├── bot/                # Модуль бота
│   ├── config.py       # Конфигурация
│   ├── handlers.py     # Обработчики сообщений
│   └── main.py         # Точка входа
├── db/                 # Модуль базы данных
│   ├── database.py     # Пул соединений
│   ├── load_data.py    # Загрузка данных
│   └── schema.sql      # Схема БД
├── nl/                 # Модуль обработки естественного языка
│   ├── parser.py       # Парсер (взаимодействие с LLM)
│   ├── prompt.py       # Промпты для LLM
│   └── schemas.py      # Схемы данных
├── data/               # Данные
│   └── videos.json     # JSON-файл с данными (нужно скачать)
├── docker/             # Docker конфигурация
│   └── postgres/
│       └── init.sql
├── docker-compose.yml  # Docker Compose конфигурация
├── Dockerfile          # Dockerfile для бота
├── requirements.txt    # Зависимости Python
├── README.md           # Документация
├── OLLAMA_SETUP.md     # Инструкция по настройке Ollama
└── DEVELOPMENT_PLAN.md # План разработки
```

## Описание промпта и схемы данных для LLM

### Схема данных (DATABASE_SCHEMA)

В `nl/schemas.py` содержится подробное описание структуры БД:
- Описание таблиц `videos` и `video_snapshots`
- Описание всех полей и их типов
- Важные моменты использования (когда использовать какую таблицу)

### Системный промпт

В `nl/prompt.py` содержится системный промпт, который:
- Описывает роль LLM (эксперт по преобразованию запросов)
- Содержит полное описание схемы БД
- Содержит правила преобразования с примерами:
  - "Сколько всего видео" → count по таблице videos
  - "Сколько видео у креатора" → count с фильтром по creator_id
  - "Сколько видео набрало больше X просмотров" → count с comparison_filter
  - "На сколько просмотров выросли" → sum по delta_views_count из snapshots
  - "Сколько разных видео получали новые просмотры" → distinct_count с фильтром delta > 0
- Содержит правила обработки дат
- Объясняет, когда использовать какую таблицу

### Структурированный ответ

LLM возвращает JSON согласно схеме `QueryRequest`:
- `table` - таблица (videos или snapshots)
- `metric_type` - тип метрики (count, sum, distinct_count)
- `metric_field` - поле для метрики (если нужно)
- `date_filter` - фильтр по дате
- `creator_id_filter` - фильтр по creator_id
- `comparison_filter` - фильтр сравнения

Этот JSON валидируется через Pydantic и преобразуется в SQL детерминированным кодом.

## Лицензия

Проект создан в рамках тестового задания.
