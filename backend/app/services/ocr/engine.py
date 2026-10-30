"""Интерфейс движка распознавания.

Движок получает уже провалидированное и предобработанное изображение и
возвращает сегменты одной страницы. Всё, что связано с валидацией,
предобработкой, склейкой страниц и ретраями, — в `pipeline.py`, чтобы новый
движок (HTR-модель, облачный адаптер) добавлялся без правок конвейера.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from PIL import Image

from app.services.ocr.types import PageRecognition


class OcrEngine(Protocol):
    """Контракт движка. Реализации не должны менять переданное изображение."""

    #: Имя для диагностики и поля `RecognitionRun.engine`.
    name: str
    #: Версия движка и модели для воспроизводимости.
    version: str
    #: Язык распознавания в терминах движка (для Tesseract — `rus`).
    language: str

    def recognize_page(self, image: Image.Image, *, page_index: int) -> PageRecognition:
        """Распознать одну страницу.

        Args:
            image: изображение в оттенках серого, уже предобработанное.
            page_index: индекс страницы с 0; попадает в каждый сегмент.

        Returns:
            Текст страницы и сегменты в порядке чтения. Пустой текст —
            страница без распознаваемого содержимого.

        Raises:
            OcrEngineError: движок не смог обработать страницу.
            OcrEngineUnavailableError: движок не установлен.
        """
        ...


@runtime_checkable
class EngineFactory(Protocol):
    """Создаёт движок по требованию (движок может быть тяжёлым)."""

    def __call__(self) -> OcrEngine: ...
