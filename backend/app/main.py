"""Точка входа backend AI Exam Checker.

Каркас T-005: только GET /health, конфигурация и единый формат ошибок.
Полноценная проверка ответов (OCR, оценка, экспертная проверка) — T-006+.
"""

import logging
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import health

logger = logging.getLogger("ai-exam-checker")

SERVICE_NAME = "ai-exam-checker-backend"
SERVICE_VERSION = "0.1.0"


def configure_logging() -> None:
    """Структурный вывод в stdout; секреты и тексты ответов не логируются."""
    logging.basicConfig(
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


async def request_id_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Эхо X-Request-ID: при отсутствии заголовка генерируется UUID v4."""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


def create_app() -> FastAPI:
    """Собирает приложение. Вынесено в функцию для тестов."""
    configure_logging()

    app = FastAPI(
        title="AI Exam Checker API",
        description=(
            "Исследовательский прототип проверки развёрнутых ответов ЕГЭ по истории. "
            "Этап T-005: каркас с health-check; полноценная функциональность в разработке."
        ),
        version=SERVICE_VERSION,
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
        openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
    )

    app.add_middleware(CORSMiddleware, allow_origins=[], allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"])
    app.middleware("http")(request_id_middleware)

    if settings.cors_origins:
        # Внешние origin разрешаются только явной настройкой CORS_ORIGINS.
        app.user_middleware.clear()
        app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                           allow_credentials=True, allow_methods=["*"],
                           allow_headers=["*"])
        app.middleware("http")(request_id_middleware)

    app.include_router(health.router, prefix=settings.API_V1_PREFIX)

    # Docker HEALTHCHECK и платформенные пробы используют короткий путь.
    app.add_api_route("/health", _liveness, methods=["GET"], include_in_schema=False)

    return app


async def _liveness() -> dict[str, str]:
    """Короткий health для Docker HEALTHCHECK и внешних проб."""
    return {"status": "ok"}


app = create_app()


def main() -> None:
    """Запуск dev-сервера: python -m app.main."""
    import uvicorn

    uvicorn.run("app.main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=False)


if __name__ == "__main__":
    main()
