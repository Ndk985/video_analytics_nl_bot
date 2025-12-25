from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@db:5432/postgres"
)

# LLM конфигурация (поддержка разных провайдеров)
# Режим работы: "ollama" (локально), "deepseek", "openai" или другой
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")

# API ключи (нужны только для облачных провайдеров)
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# URL и модель (зависят от провайдера)
if LLM_PROVIDER == "ollama":
    # Ollama работает локально
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://host.docker.internal:11434/v1")
    LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama")  # Ollama не требует ключа, но SDK требует
elif LLM_PROVIDER == "deepseek":
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
    LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
    LLM_API_KEY = DEEPSEEK_API_KEY
elif LLM_PROVIDER == "openai":
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
    LLM_API_KEY = OPENAI_API_KEY
else:
    # Кастомный провайдер
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
    LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
    LLM_API_KEY = os.getenv("LLM_API_KEY") or DEEPSEEK_API_KEY or OPENAI_API_KEY
