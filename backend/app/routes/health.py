"""GET /health — проверка живости backend.

Публичный маршрут без аутентификации (API_CONTRACT §1.1).
На этапе каркаса (T-005) проверяется только живость процесса:
PostgreSQL ещё не подключён, поэтому health не зависит от БД.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Ответ health-check."""

    status: str
    service: str
    version: str


@router.get(
    "/health",
    status_code=200,
    response_model=HealthResponse,
    summary="Проверка живости сервиса",
)
async def health() -> HealthResponse:
    """Возвращает статус процесса.

    Проверка БД появится в T-006 вместе с сессией SQLAlchemy и миграциями.
    """
    return HealthResponse(status="ok", service="ai-exam-checker-backend", version="0.1.0")
