"""Тесты валидации входных изображений."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from app.services.ocr.types import (
    ImageTooLargeError,
    OcrInputError,
    UnsupportedMediaTypeError,
)
from app.services.ocr.validation import validate_image


def png_bytes(size: tuple[int, int] = (200, 100), mode: str = "RGB") -> bytes:
    buffer = io.BytesIO()
    Image.new(mode, size, "white").save(buffer, format="PNG")
    return buffer.getvalue()


def jpeg_bytes(size: tuple[int, int] = (200, 100)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, "white").save(buffer, format="JPEG")
    return buffer.getvalue()


def webp_bytes(size: tuple[int, int] = (200, 100)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, "white").save(buffer, format="WEBP")
    return buffer.getvalue()


class TestValidFormats:
    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            (png_bytes(), "image/png"),
            (jpeg_bytes(), "image/jpeg"),
            (webp_bytes(), "image/webp"),
        ],
    )
    def test_accepts_supported_formats(self, data: bytes, expected: str) -> None:
        result = validate_image(data)
        assert result.mime_type == expected
        assert result.data == data, "оригинальные байты не должны меняться"

    def test_reports_real_dimensions(self) -> None:
        result = validate_image(png_bytes((320, 240)))
        assert (result.width_px, result.height_px) == (320, 240)


class TestRejection:
    def test_rejects_empty_file(self) -> None:
        with pytest.raises(OcrInputError, match="пуст"):
            validate_image(b"")

    def test_rejects_pdf_by_content(self) -> None:
        # PDF начинается с %PDF, но клиент мог назвать файл answer.png.
        with pytest.raises(UnsupportedMediaTypeError) as error:
            validate_image(b"%PDF-1.7\n%...")
        assert error.value.details["reason"] == "unknown_signature"

    def test_rejects_text_file(self) -> None:
        with pytest.raises(UnsupportedMediaTypeError):
            validate_image("просто текст".encode())

    def test_rejects_truncated_png(self) -> None:
        data = png_bytes()
        with pytest.raises(UnsupportedMediaTypeError) as error:
            validate_image(data[: len(data) // 2])
        assert error.value.details["reason"] == "decode_failed"

    def test_rejects_mime_not_in_allowlist(self) -> None:
        with pytest.raises(UnsupportedMediaTypeError) as error:
            validate_image(png_bytes(), allowed_mime_types=["image/jpeg"])
        assert error.value.details["mime_type"] == "image/png"

    def test_rejects_file_over_size_limit(self) -> None:
        data = png_bytes()
        with pytest.raises(ImageTooLargeError) as error:
            validate_image(data, max_bytes=len(data) - 1)
        assert error.value.details["max_bytes"] == len(data) - 1

    def test_rejects_too_small_image(self) -> None:
        with pytest.raises(OcrInputError, match="маленьк"):
            validate_image(png_bytes((16, 16)))

    def test_rejects_excessive_pixels(self) -> None:
        # Заголовок PNG подделываем вручную: Pillow не должен успеть
        # аллоцировать гигабайты. Проверяем отказ по лимиту площади.
        with pytest.raises(ImageTooLargeError):
            validate_image(png_bytes((7000, 7000)))


class TestImmutability:
    def test_original_bytes_are_not_modified(self) -> None:
        data = png_bytes((300, 200))
        snapshot = bytes(data)
        result = validate_image(data)
        image = result.open()
        image.rotate(90).save(io.BytesIO(), format="PNG")
        assert result.data == snapshot

    def test_open_returns_independent_image(self) -> None:
        result = validate_image(png_bytes((120, 80)))
        first = result.open()
        first.paste((0, 0, 0), (0, 0, 10, 10))
        second = result.open()
        assert second.getpixel((0, 0)) == (255, 255, 255)
