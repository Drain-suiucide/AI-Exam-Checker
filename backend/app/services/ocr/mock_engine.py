"""Mock-движок: детерминированный результат без внешних зависимостей.

Нужен для тестов, демо-режима и CI, где Tesseract может быть не установлен.
Текст не «придумывается» из изображения — он возвращает заранее заданную
строку, поэтому годится только для проверки контракта, а не качества.
"""

from __future__ import annotations

from PIL import Image

from app.services.ocr.types import OcrSegment, PageRecognition

DEFAULT_MOCK_TEXT = (
    "Понятие раскрыто: реформа — это изменение в какой-либо сфере жизни общества. "
    "Исторический факт: реформа 1861 года отменила крепостное право."
)

#: Сколько символов приходится на один искусственный сегмент.
_SEGMENT_CHARS = 40


class MockEngine:
    """Возвращает заданный текст, разбитый на сегменты по странице."""

    name = "mock"
    version = "1"
    language = "rus"

    def __init__(self, text: str = DEFAULT_MOCK_TEXT) -> None:
        self._text = text

    def recognize_page(self, image: Image.Image, *, page_index: int) -> PageRecognition:
        if page_index > 0:
            # На второй и далее странице текста нет — так проверяется склейка.
            return PageRecognition(text="", segments=[])
        segments: list[OcrSegment] = []
        for index, start in enumerate(range(0, len(self._text), _SEGMENT_CHARS)):
            chunk = self._text[start : start + _SEGMENT_CHARS]
            # bbox — искусственная сетка сверху вниз, чтобы контракт был полным.
            top = min(0.9, index * 0.05)
            segments.append(
                OcrSegment(
                    index=index,
                    page_index=page_index,
                    text=chunk,
                    char_start=start,
                    char_end=start + len(chunk),
                    confidence=0.99,
                    bbox=(0.05, top, 0.95, top + 0.04),
                )
            )
        return PageRecognition(text=self._text, segments=segments)
