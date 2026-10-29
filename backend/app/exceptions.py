"""Единый формат ошибок (согласно API_CONTRACT §1.2)."""

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError


class BaseAPIError(Exception):
    code: str = "INTERNAL_ERROR"
    status_code = 500
    message = "Внутренняя ошибка сервера."


async def api_exception_handler(request: Request, exc: BaseAPIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": None,
                "request_id": getattr(
                    request.state, "request_id", request.headers.get("x-request-id")
                ),
            }
        },
        headers={"Cache-Control": "no-store"},
    )


async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    from app.config import get_request_id

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Ошибка валидации запроса.",
                "details": {"fields": exc.errors()},
                "request_id": get_request_id(request),
            }
        },
        headers={"Cache-Control": "no-store"},
    )


async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Ошибка валидации запроса.",
                "details": {"fields": exc.errors()},
                "request_id": getattr(
                    request.state, "request_id", request.headers.get("x-request-id")
                ),
            }
        },
        headers={"Cache-Control": "no-store"},
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.headers.get("X-Error-Code", exc.status_code),
                "message": exc.detail,
                "details": None,
                "request_id": getattr(
                    request.state, "request_id", request.headers.get("x-request-id")
                ),
            }
        },
        headers={"Cache-Control": "no-store"},
    )


BASE_EXCEPTIONS = {
    BaseAPIError: api_exception_handler,
    ValidationError: validation_exception_handler,
    HTTPException: http_exception_handler,
    RequestValidationError: request_validation_exception_handler,
}


class InvalidStateError(BaseAPIError):
    code = "INVALID_STATE"
    status_code = 409
    message = "Действие недоступно в текущем состоянии отправки."


class NotFoundError(BaseAPIError):
    code = "NOT_FOUND"
    status_code = 404
    message = "Ресурс не найден."


class UnauthorizedError(BaseAPIError):
    code = "UNAUTHORIZED"
    status_code = 401
    message = "Отсутствует авторизация."


class ForbiddenError(BaseAPIError):
    code = "FORBIDDEN"
    status_code = 403
    message = "Доступ запрещён."


class RateLimitedError(BaseAPIError):
    code = "RATE_LIMITED"
    status_code = 429
    message = "Превышен лимит запросов."
