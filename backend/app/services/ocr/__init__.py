"""Модуль распознавания текста (OCR/HTR).

Изолированный слой: на вход — байты изображений, на выход — текст, сегменты
с координатами и уверенностью, диагностика. Не знает о БД, HTTP и оценивании.

Точка входа — `recognize_pages`; детали — в `docs/research/ocr_comparison.md`
и `docs/evaluation/ocr_evaluation.md`.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.services.ocr.factory import build_engine
from app.services.ocr.pipeline import DEFAULT_MAX_ATTEMPTS, OcrPipeline
from app.services.ocr.types import (
    BBox,
    ImageTooLargeError,
    OcrDiagnostics,
    OcrEngineError,
    OcrEngineUnavailableError,
    OcrError,
    OcrInputError,
    OcrPageResult,
    OcrResult,
    OcrSegment,
    PageRecognition,
    UnsupportedMediaTypeError,
)
from app.services.ocr.validation import ValidatedImage, validate_image

__all__ = [
    "BBox",
    "ImageTooLargeError",
    "OcrDiagnostics",
    "OcrEngine",
    "OcrEngineError",
    "OcrEngineUnavailableError",
    "OcrError",
    "OcrInputError",
    "OcrPageResult",
    "OcrPipeline",
    "OcrResult",
    "OcrSegment",
    "PageRecognition",
    "UnsupportedMediaTypeError",
    "ValidatedImage",
    "build_engine",
    "recognize_pages",
    "validate_image",
]


def recognize_pages(
    pages: Sequence[bytes],
    *,
    engine_name: str | None = None,
    allowed_mime_types: list[str] | None = None,
    max_bytes: int | None = None,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    deskew: bool = True,
) -> OcrResult:
    """Распознать страницы изображений.

    Args:
        pages: байты страниц в порядке следования.
        engine_name: переопределить `OCR_ENGINE` (например, `mock` в тестах).
        allowed_mime_types: MIME из `limits.allowed_mime_types` конфигурации.
        max_bytes: `limits.max_file_bytes` конфигурации.
        max_attempts: число попыток на страницу при временной ошибке.
        deskew: выравнивать ли наклон.

    Returns:
        `OcrResult` с текстом, сегментами и диагностикой.
    """
    engine = build_engine(engine_name)
    pipeline = OcrPipeline(engine, max_attempts=max_attempts, deskew=deskew)
    return pipeline.recognize(
        pages,
        allowed_mime_types=allowed_mime_types,
        max_bytes=max_bytes,
    )
