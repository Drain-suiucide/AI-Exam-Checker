"""Выбор движка по настройке `OCR_ENGINE`.

Новый движок (HTR-модель, облачный адаптер) добавляется здесь одной ветвью;
конвейер и маршруты при этом не меняются.
"""

from __future__ import annotations

from app.config import settings
from app.services.ocr.engine import OcrEngine
from app.services.ocr.mock_engine import MockEngine
from app.services.ocr.types import OcrEngineUnavailableError


def build_engine(name: str | None = None) -> OcrEngine:
    """Собрать движок по имени из конфигурации.

    Args:
        name: `mock` | `tesseract` | `easyocr`. По умолчанию — из настроек.

    Raises:
        OcrEngineUnavailableError: движок не поддерживается или не установлен.
    """
    engine_name = (name or settings.OCR_ENGINE).lower()

    if engine_name == "mock":
        return MockEngine()

    if engine_name == "tesseract":
        # Импорт внутри ветви: pytesseract не нужен в mock-режиме и в тестах.
        from app.services.ocr.tesseract_engine import TesseractEngine

        return TesseractEngine(
            language=settings.OCR_LANGUAGE,
            tesseract_cmd=settings.OCR_TESSERACT_CMD,
            tessdata_prefix=settings.OCR_TESSDATA_PREFIX,
        )

    if engine_name == "easyocr":
        raise OcrEngineUnavailableError(
            "Движок easyocr не реализован.",
            details={
                "engine": engine_name,
                "reason": "not_implemented",
                "note": "См. docs/research/ocr_comparison.md — рукописный текст не поддерживается",
            },
        )

    raise OcrEngineUnavailableError(
        "Неизвестный движок распознавания.",
        details={"engine": engine_name},
    )
