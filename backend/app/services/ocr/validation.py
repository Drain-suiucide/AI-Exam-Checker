"""Валидация входных изображений до передачи в движок.

Тип определяется по содержимому (сигнатуре), а не по имени файла или
`Content-Type` от клиента — этого требует API_CONTRACT §1.6 (415 по
содержимому). Файл читается в память один раз и дальше не изменяется:
оригинал должен остаться неизменным (требование задачи).
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError

from app.services.ocr.types import (
    ImageTooLargeError,
    OcrInputError,
    UnsupportedMediaTypeError,
)

#: Разрешённые форматы Pillow -> MIME из контракта.
_FORMAT_TO_MIME = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}

#: Сигнатуры, по которым отсекаем заведомо не-изображения до разбора Pillow.
_MAGIC = (
    (b"\xff\xd8\xff", "JPEG"),
    (b"\x89PNG\r\n\x1a\n", "PNG"),
    (b"RIFF", "WEBP"),  # проверяется дополнительно ниже
)

#: Верхняя граница сторон и площади: защита от «decompression bomb».
MAX_SIDE_PX = 20_000
MAX_PIXELS = 40_000_000  # 40 Мпикс — с запасом для фото с телефона
#: Нижняя граница: на меньшем тексте OCR заведомо не работает.
MIN_SIDE_PX = 32
#: Pillow по умолчанию предупреждает на > 89 Мпикс; мы ограничиваем раньше.


@dataclass(frozen=True, slots=True)
class ValidatedImage:
    """Проверенное изображение: оригинальные байты + метаданные."""

    data: bytes
    mime_type: str
    width_px: int
    height_px: int

    def open(self) -> Image.Image:
        """Открыть копию изображения. Оригинальные байты не меняются."""
        image = Image.open(io.BytesIO(self.data))
        image.load()
        return image


def _sniff_mime(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def validate_image(
    data: bytes,
    *,
    allowed_mime_types: list[str] | None = None,
    max_bytes: int | None = None,
) -> ValidatedImage:
    """Проверить байты изображения и вернуть метаданные.

    Raises:
        UnsupportedMediaTypeError: сигнатура не JPEG/PNG/WebP либо Pillow не
            смог разобрать файл.
        ImageTooLargeError: превышен `max_bytes` или пиксельные лимиты.
        OcrInputError: файл пуст.
    """
    if not data:
        raise OcrInputError("Файл пуст.", details={"reason": "empty"})
    if max_bytes is not None and len(data) > max_bytes:
        raise ImageTooLargeError(
            "Размер файла превышает допустимый.",
            details={"size_bytes": len(data), "max_bytes": max_bytes},
        )

    sniffed = _sniff_mime(data)
    if sniffed is None:
        raise UnsupportedMediaTypeError(
            "Содержимое файла не является изображением JPEG, PNG или WebP.",
            details={"reason": "unknown_signature"},
        )
    if allowed_mime_types and sniffed not in allowed_mime_types:
        raise UnsupportedMediaTypeError(
            "Тип изображения не разрешён конфигурацией.",
            details={"mime_type": sniffed, "allowed": list(allowed_mime_types)},
        )

    # Pillow нужен, чтобы убедиться, что файл действительно декодируется,
    # и получить реальные размеры (заголовок можно подделать).
    try:
        with Image.open(io.BytesIO(data)) as probe:
            probe.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise UnsupportedMediaTypeError(
            "Файл повреждён или не является изображением.",
            details={"reason": "decode_failed"},
        ) from exc

    try:
        with Image.open(io.BytesIO(data)) as probe:
            width, height = probe.size
            fmt = (probe.format or "").upper()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise UnsupportedMediaTypeError(
            "Файл повреждён или не является изображением.",
            details={"reason": "decode_failed"},
        ) from exc

    mime_type = _FORMAT_TO_MIME.get(fmt)
    if mime_type is None or mime_type != sniffed:
        raise UnsupportedMediaTypeError(
            "Формат файла не совпадает с его содержимым.",
            details={"format": fmt, "sniffed": sniffed},
        )

    if width < MIN_SIDE_PX or height < MIN_SIDE_PX:
        raise OcrInputError(
            "Изображение слишком маленькое для распознавания.",
            details={"width_px": width, "height_px": height, "min_side_px": MIN_SIDE_PX},
        )
    if width > MAX_SIDE_PX or height > MAX_SIDE_PX or width * height > MAX_PIXELS:
        raise ImageTooLargeError(
            "Разрешение изображения превышает допустимое.",
            details={
                "width_px": width,
                "height_px": height,
                "max_side_px": MAX_SIDE_PX,
                "max_pixels": MAX_PIXELS,
            },
        )

    return ValidatedImage(data=data, mime_type=mime_type, width_px=width, height_px=height)
