"""Общие зависимости FastAPI."""
from fastapi import Request
from app.config import settings


def get_settings_dep() -> dict:
    """Публичная конфигурация (без секретов)."""
    return {
        "environment": settings.ENVIRONMENT,
        "version": "0.1.0",
        "api_version": settings.API_V1_PREFIX.lstrip("/"),
        "demo_mode": settings.DEMO_MODE,
        "ocr_engine": settings.OCR_ENGINE,
        "llm_provider": settings.LLM_PROVIDER,
    }


def get_request_id(request: Request) -> str | None:
    """X-Request-ID из заголовка или None (не генерируем на этом уровне)."""
    return request.headers.get("x-request-id")
