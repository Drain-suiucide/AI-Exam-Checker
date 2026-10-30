"""Конвейер распознавания: валидация -> предобработка -> OCR -> склейка.

Модуль не знает про БД и HTTP. Вход — список байтов страниц в порядке
следования, выход — `OcrResult`, который маршрут сохраняет в
`Transcription.ocr_data` и `Transcription.text`.

Правила, зафиксированные в задаче:
- оригинальные байты не изменяются и не перезаписываются;
- автоматически распознанный текст не «улучшается» и не правится моделью;
- confidence переносится как есть (вспомогательная характеристика);
- частичный сбой страницы не уничтожает результат остальных страниц, но
  помечается как `partial`.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Sequence
from dataclasses import replace

from app.services.ocr.engine import OcrEngine
from app.services.ocr.preprocess import PreprocessedPage, preprocess
from app.services.ocr.types import (
    OcrDiagnostics,
    OcrEngineError,
    OcrError,
    OcrPageResult,
    OcrResult,
    OcrSegment,
    mean_confidence,
)
from app.services.ocr.validation import ValidatedImage, validate_image

logger = logging.getLogger(__name__)

#: Разделитель страниц в итоговом тексте: две переводные строки.
PAGE_SEPARATOR = "\n\n"

#: Сколько раз пытаться распознать страницу при временной ошибке.
DEFAULT_MAX_ATTEMPTS = 2
#: Базовая пауза между попытками, секунды (удваивается).
DEFAULT_RETRY_DELAY = 0.25


class OcrPipeline:
    """Оркестратор распознавания набора страниц."""

    def __init__(
        self,
        engine: OcrEngine,
        *,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        sleep: Callable[[float], None] = time.sleep,
        deskew: bool = True,
    ) -> None:
        self._engine = engine
        self._max_attempts = max(1, max_attempts)
        self._retry_delay = retry_delay
        self._sleep = sleep
        self._deskew = deskew

    def recognize(
        self,
        pages: Sequence[bytes],
        *,
        allowed_mime_types: list[str] | None = None,
        max_bytes: int | None = None,
    ) -> OcrResult:
        """Распознать страницы.

        Args:
            pages: байты изображений в порядке следования.
            allowed_mime_types: разрешённые MIME из конфигурации экзамена.
            max_bytes: максимальный размер одного файла.

        Raises:
            OcrInputError: хотя бы одна страница не прошла валидацию.
                Ошибка входных данных не ретраится и прерывает прогон:
                бессмысленно распознавать набор, часть которого невалидна.
            OcrEngineUnavailableError: движок не установлен.
            OcrEngineError: ни одна страница не распознана.
        """
        if not pages:
            raise OcrError("Не передано ни одной страницы.", details={"reason": "no_pages"})

        started = time.monotonic()
        validated = [
            validate_image(data, allowed_mime_types=allowed_mime_types, max_bytes=max_bytes)
            for data in pages
        ]

        page_results: list[OcrPageResult] = []
        page_errors: list[dict[str, object]] = []
        attempts_used = 0

        for page_index, page in enumerate(validated):
            result, attempts = self._recognize_page_with_retry(page, page_index=page_index)
            attempts_used = max(attempts_used, attempts)
            if result is not None:
                page_results.append(result)
            else:
                page_errors.append(
                    {
                        "page_index": page_index,
                        "code": "OCR_ENGINE_FAILED",
                        "message": "Страница не распознана.",
                    }
                )

        if not page_results:
            raise OcrEngineError(
                "Не удалось распознать ни одной страницы.",
                details={"page_errors": page_errors},
            )

        text, segments = _assemble(page_results)

        preprocessing: list[str] = []
        warnings: list[str] = []
        for page in page_results:
            for step in page.preprocessing:
                if step not in preprocessing:
                    preprocessing.append(step)
            for warning in page.warnings:
                if warning not in warnings:
                    warnings.append(warning)

        duration_ms = int((time.monotonic() - started) * 1000)
        diagnostics = OcrDiagnostics(
            engine=self._engine.name,
            engine_version=self._engine.version,
            language=self._engine.language,
            page_count=len(validated),
            duration_ms=duration_ms,
            attempts=attempts_used,
            preprocessing=tuple(preprocessing),
            warnings=tuple(warnings),
            page_errors=tuple(page_errors),
        )

        return OcrResult(
            text=text,
            pages=tuple(page_results),
            segments=tuple(segments),
            mean_confidence=mean_confidence([segment.confidence for segment in segments]),
            diagnostics=diagnostics,
            partial=bool(page_errors),
        )

    def _recognize_page_with_retry(
        self, page: ValidatedImage, *, page_index: int
    ) -> tuple[OcrPageResult | None, int]:
        """Распознать страницу с повторами. Возвращает (результат, число попыток)."""
        prepared: PreprocessedPage | None = None
        last_error: OcrError | None = None

        for attempt in range(1, self._max_attempts + 1):
            try:
                if prepared is None:
                    prepared = preprocess(page.open(), deskew=self._deskew)
                recognition = self._engine.recognize_page(
                    prepared.image.copy(), page_index=page_index
                )
            except OcrError as exc:
                last_error = exc
                logger.warning(
                    "OCR page failed",
                    extra={
                        "page_index": page_index,
                        "attempt": attempt,
                        "code": exc.code,
                        "transient": exc.transient,
                    },
                )
                if not exc.transient:
                    # Постоянная ошибка: повтор не поможет, сразу к следующей странице.
                    break
                if attempt < self._max_attempts:
                    self._sleep(self._retry_delay * (2 ** (attempt - 1)))
                continue
            except Exception as exc:  # noqa: BLE001 - движок может бросить что угодно
                last_error = OcrEngineError(
                    "Непредвиденная ошибка движка.",
                    details={"page_index": page_index, "reason": type(exc).__name__},
                )
                logger.exception("OCR page crashed", extra={"page_index": page_index})
                break

            return (
                OcrPageResult(
                    page_index=page_index,
                    width_px=page.width_px,
                    height_px=page.height_px,
                    text=recognition.text,
                    segments=recognition.segments,
                    mean_confidence=mean_confidence(
                        [segment.confidence for segment in recognition.segments]
                    ),
                    preprocessing=prepared.steps,
                    rotation_applied_deg=prepared.rotation_applied_deg,
                    warnings=prepared.warnings,
                ),
                attempt,
            )

        if last_error is not None and not last_error.transient:
            # Постоянная ошибка страницы: остальные страницы всё ещё могут
            # быть обработаны. Решение о полном провале принимает recognize().
            return None, self._max_attempts
        return None, self._max_attempts


def _assemble(page_results: list[OcrPageResult]) -> tuple[str, list[OcrSegment]]:
    """Склеить страницы в единый текст с переиндексацией сегментов.

    Смещения сегментов пересчитываются относительно итоговой строки, поэтому
    `char_start`/`char_end` в `ocr_data` всегда указывают в `Transcription.text`.
    """
    parts: list[str] = []
    assembled: list[OcrSegment] = []
    cursor = 0
    index = 0

    for position, page in enumerate(page_results):
        if position > 0:
            parts.append(PAGE_SEPARATOR)
            cursor += len(PAGE_SEPARATOR)

        offset = cursor
        for segment in page.segments:
            assembled.append(
                replace(
                    segment,
                    index=index,
                    char_start=offset + segment.char_start,
                    char_end=offset + segment.char_end,
                )
            )
            index += 1
        parts.append(page.text)
        cursor += len(page.text)

    return "".join(parts), assembled
