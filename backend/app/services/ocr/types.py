"""Типы результатов OCR.

Модуль изолирован: ничего не знает о БД, HTTP и оценивании. Возвращает
структуры, которые маршрут `POST /submissions/{id}/recognize` сериализует в
формат `API_CONTRACT.md` §2.3 (`Transcription.ocr`).

Важно про `confidence`: это вспомогательная характеристика движка, а не
вероятность правильности распознавания. Tesseract выдаёт высокую уверенность
и на ошибочно распознанных словах (см. docs/evaluation/ocr_evaluation.md),
поэтому значения нельзя использовать как доказательство корректности.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Нормализованный bbox: (x0, y0, x1, y1) в долях ширины/высоты страницы, 0..1.
BBox = tuple[float, float, float, float]


class OcrError(Exception):
    """Базовая ошибка модуля распознавания."""

    code = "OCR_ERROR"
    #: transient=True означает, что повторная попытка может помочь.
    transient = False

    def __init__(
        self,
        message: str,
        *,
        details: dict | None = None,
        transient: bool | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}
        if transient is not None:
            self.transient = transient


class OcrInputError(OcrError):
    """Входной файл не прошёл валидацию. Повтор не поможет."""

    code = "OCR_INPUT_INVALID"


class UnsupportedMediaTypeError(OcrInputError):
    """Содержимое файла не является поддерживаемым изображением."""

    code = "UNSUPPORTED_MEDIA_TYPE"


class ImageTooLargeError(OcrInputError):
    """Изображение превышает допустимые размеры."""

    code = "IMAGE_TOO_LARGE"


class OcrEngineError(OcrError):
    """Движок распознавания не смог обработать страницу."""

    code = "OCR_ENGINE_FAILED"


class OcrEngineUnavailableError(OcrEngineError):
    """Движок не установлен или не сконфигурирован."""

    code = "OCR_ENGINE_UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class OcrSegment:
    """Распознанный фрагмент (слово) и его положение на странице."""

    index: int
    page_index: int
    text: str
    char_start: int
    char_end: int
    confidence: float | None
    bbox: BBox | None

    def to_contract(self) -> dict[str, object]:
        """Форма из API_CONTRACT.md §2.3."""
        return {
            "index": self.index,
            "page_index": self.page_index,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "confidence": self.confidence,
            "bbox": list(self.bbox) if self.bbox is not None else None,
        }


@dataclass(frozen=True, slots=True)
class PageRecognition:
    """Результат движка по одной странице.

    `text` — то, что реально распознано; `segments` — привязка фрагментов к
    `text` и к изображению. Текст передаётся отдельно, а не собирается из
    сегментов: движок знает про переводы строк и пробелы, а склейка «по
    сегментам» потеряла бы разделители.
    """

    text: str
    segments: list[OcrSegment] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class OcrPageResult:
    """Результат по одной странице до склейки в общий текст."""

    page_index: int
    width_px: int
    height_px: int
    text: str = ""
    segments: list[OcrSegment] = field(default_factory=list)
    mean_confidence: float | None = None
    preprocessing: tuple[str, ...] = ()
    rotation_applied_deg: float = 0.0
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OcrDiagnostics:
    """Диагностика прогона: для логов и разбора качества, не для пользователя."""

    engine: str
    engine_version: str
    language: str
    page_count: int
    duration_ms: int
    attempts: int
    #: Шаги предобработки, применённые хотя бы к одной странице.
    preprocessing: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    #: Ошибки страниц, не прервавшие весь прогон (частичный успех).
    page_errors: tuple[dict[str, object], ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "engine": self.engine,
            "engine_version": self.engine_version,
            "language": self.language,
            "page_count": self.page_count,
            "duration_ms": self.duration_ms,
            "attempts": self.attempts,
            "preprocessing": list(self.preprocessing),
            "warnings": list(self.warnings),
            "page_errors": [dict(item) for item in self.page_errors],
        }


@dataclass(frozen=True, slots=True)
class OcrResult:
    """Итог распознавания набора страниц."""

    text: str
    pages: tuple[OcrPageResult, ...]
    segments: tuple[OcrSegment, ...]
    mean_confidence: float | None
    diagnostics: OcrDiagnostics
    #: Хотя бы одна страница не распознана: текст неполный.
    partial: bool = False

    def to_contract(self) -> dict[str, object]:
        """Значение поля `ocr` в `Transcription` (API_CONTRACT.md §2.3)."""
        return {
            "mean_confidence": self.mean_confidence,
            "segments": [segment.to_contract() for segment in self.segments],
        }


def mean_confidence(values: list[float | None]) -> float | None:
    """Среднее по известным значениям; None, если известных нет.

    Округляется до 4 знаков, чтобы не тащить в JSON хвосты float.
    """
    known = [value for value in values if value is not None]
    if not known:
        return None
    return round(sum(known) / len(known), 4)
