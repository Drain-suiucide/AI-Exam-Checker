"""Конфигурация приложения из переменных окружения (pydantic-settings).

Все значения читаются из окружения или `.env`; секретов в коде нет.
Обязательных секретов на этапе каркаса нет: DATABASE_URL не нужен для /health.
"""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки backend. Имена переменных совпадают с ARCHITECTURE §9."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # --- окружение ---
    ENVIRONMENT: Literal["development", "staging", "production", "testing"] = "development"
    DEBUG: bool = False

    # --- backend ---
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: str = ""
    ALLOW_UNAPPROVED_CONFIG: bool = False

    # --- база данных ---
    # На этапе каркаса необязательна: /health не зависит от PostgreSQL (T-005).
    DATABASE_URL: SecretStr | None = None
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    # --- режимы адаптеров ---
    DEMO_MODE: bool = True
    OCR_ENGINE: Literal["mock", "tesseract", "easyocr"] = "mock"
    LLM_PROVIDER: Literal["mock", "openai", "anthropic"] = "mock"

    # --- OCR ---
    #: Язык распознавания (модели Tesseract через «+»,
    #: например `rus+eng`; `eng` нужен для римских цифр).
    OCR_LANGUAGE: str = "rus+eng"
    #: Каталог с `*.traineddata`; пусто — системный каталог Tesseract.
    OCR_TESSDATA_PREFIX: str | None = None
    #: Путь к бинарнику `tesseract`, если его нет в PATH.
    OCR_TESSERACT_CMD: str | None = None
    #: Попыток на страницу при временной ошибке движка.
    OCR_MAX_ATTEMPTS: int = 2

    @property
    def cors_origins(self) -> list[str]:
        """CORS_ORIGINS хранится строкой через запятую, как в .env."""
        return [item.strip() for item in self.CORS_ORIGINS.split(",") if item.strip()]

    @property
    def is_db_configured(self) -> bool:
        return self.DATABASE_URL is not None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Кэшированный экземпляр настроек."""
    return Settings()


settings = get_settings()
