"""Тесты движка Tesseract.

Тесты, требующие установленного бинарника и русской модели, помечены
`requires_tesseract` и пропускаются, если движка нет. Это осознанно:
CI без OCR должен проходить, а локально и в среде с моделями — проверять
реальное распознавание.

Путь к движку и моделям берётся из переменных окружения:
`TESSERACT_CMD` и `OCR_TESSDATA_PREFIX`.
"""

from __future__ import annotations

import os
import shutil

import pytest
from PIL import Image, ImageDraw, ImageFont

from app.services.ocr.tesseract_engine import (
    DEFAULT_CONFIG,
    TesseractEngine,
    _normalize_text,
    _recognition_from_data,
)
from app.services.ocr.types import OcrEngineError, OcrEngineUnavailableError

TESSERACT_CMD = os.environ.get("TESSERACT_CMD") or shutil.which("tesseract")
TESSDATA_PREFIX = os.environ.get("OCR_TESSDATA_PREFIX") or os.environ.get("TESSDATA_PREFIX")

requires_tesseract = pytest.mark.skipif(
    not TESSERACT_CMD,
    reason="Tesseract не установлен (TESSERACT_CMD)",
)


def _engine(config: str = DEFAULT_CONFIG) -> TesseractEngine:
    engine = TesseractEngine(
        language="rus",
        tesseract_cmd=TESSERACT_CMD,
        tessdata_prefix=TESSDATA_PREFIX,
        config=config,
    )
    engine.ensure_available()
    return engine


def render(text: str, *, size: int = 32, width: int = 900) -> Image.Image:
    """Отрисовать текст системным шрифтом с кириллицей."""
    font = None
    for candidate in (r"C:\Windows\Fonts\times.ttf", r"C:\Windows\Fonts\arial.ttf"):
        try:
            font = ImageFont.truetype(candidate, size)
            break
        except OSError:
            continue
    if font is None:
        pytest.skip("Нет системного шрифта с кириллицей")

    image = Image.new("RGB", (width, size * 3), "white")
    draw = ImageDraw.Draw(image)
    draw.text((30, 30), text, font=font, fill=(20, 20, 20))
    return image


class TestDataParsing:
    """Разбор вывода Tesseract не требует установленного движка."""

    def test_builds_text_and_offsets(self) -> None:
        data = {
            "text": ["Понятие", "раскрыто.", ""],
            "conf": ["96", "92", "-1"],
            "page_num": [1, 1, 1],
            "block_num": [1, 1, 1],
            "par_num": [1, 1, 1],
            "line_num": [1, 1, 1],
            "left": [10, 100, 0],
            "top": [10, 10, 0],
            "width": [80, 90, 0],
            "height": [20, 20, 0],
        }
        result = _recognition_from_data(data, page_index=0, width=200, height=100)

        assert result.text == "Понятие раскрыто."
        assert [segment.text for segment in result.segments] == ["Понятие", "раскрыто."]
        for segment in result.segments:
            assert result.text[segment.char_start : segment.char_end] == segment.text

    def test_skips_negative_confidence(self) -> None:
        data = {
            "text": ["мусор", "текст"],
            "conf": ["-1", "90"],
            "page_num": [1, 1],
            "block_num": [1, 1],
            "par_num": [1, 1],
            "line_num": [1, 1],
            "left": [0, 0],
            "top": [0, 0],
            "width": [10, 10],
            "height": [10, 10],
        }
        result = _recognition_from_data(data, page_index=0, width=100, height=100)
        assert result.text == "текст"
        assert len(result.segments) == 1

    def test_newline_between_paragraphs(self) -> None:
        data = {
            "text": ["первый", "второй"],
            "conf": ["90", "90"],
            "page_num": [1, 1],
            "block_num": [1, 1],
            "par_num": [1, 2],
            "line_num": [1, 1],
            "left": [0, 0],
            "top": [0, 50],
            "width": [10, 10],
            "height": [10, 10],
        }
        result = _recognition_from_data(data, page_index=0, width=100, height=100)
        assert result.text == "первый\nвторой"

    def test_bbox_is_normalized(self) -> None:
        data = {
            "text": ["слово"],
            "conf": ["80"],
            "page_num": [1],
            "block_num": [1],
            "par_num": [1],
            "line_num": [1],
            "left": [50],
            "top": [25],
            "width": [100],
            "height": [50],
        }
        segment = _recognition_from_data(data, page_index=0, width=200, height=100).segments[0]
        assert segment.bbox == (0.25, 0.25, 0.75, 0.75)

    def test_bbox_clamped_to_unit_square(self) -> None:
        data = {
            "text": ["слово"],
            "conf": ["80"],
            "page_num": [1],
            "block_num": [1],
            "par_num": [1],
            "line_num": [1],
            "left": [150],
            "top": [80],
            "width": [100],
            "height": [50],
        }
        segment = _recognition_from_data(data, page_index=0, width=200, height=100).segments[0]
        assert segment.bbox is not None
        assert all(0.0 <= value <= 1.0 for value in segment.bbox)

    def test_confidence_scaled_to_unit_interval(self) -> None:
        data = {
            "text": ["слово"],
            "conf": ["95"],
            "page_num": [1],
            "block_num": [1],
            "par_num": [1],
            "line_num": [1],
            "left": [0],
            "top": [0],
            "width": [10],
            "height": [10],
        }
        segment = _recognition_from_data(data, page_index=0, width=100, height=100).segments[0]
        assert segment.confidence == pytest.approx(0.95)


class TestTextNormalization:
    def test_converts_crlf_to_lf(self) -> None:
        assert _normalize_text("a\r\nb") == "a\nb"

    def test_strips_surrounding_whitespace(self) -> None:
        assert _normalize_text("  текст \n") == "текст"

    def test_applies_nfc(self) -> None:
        decomposed = "и\u0306"  # «й» в разложенном виде
        assert _normalize_text(decomposed) == "й"


class TestEngineAvailability:
    def test_unknown_language_reports_available(self) -> None:
        if not TESSERACT_CMD:
            pytest.skip("Tesseract не установлен")
        engine = TesseractEngine(
            language="нет-такого",
            tesseract_cmd=TESSERACT_CMD,
            tessdata_prefix=TESSDATA_PREFIX,
        )
        with pytest.raises(OcrEngineUnavailableError) as error:
            engine.ensure_available()
        assert error.value.details["language"] == "нет-такого"

    def test_missing_binary_raises(self) -> None:
        with pytest.raises(OcrEngineUnavailableError):
            TesseractEngine(
                language="rus",
                tesseract_cmd=r"C:\несуществующий\tesseract.exe",
            )

    def test_prefix_with_spaces_is_rejected(self) -> None:
        if not TESSERACT_CMD:
            pytest.skip("Tesseract не установлен")
        with pytest.raises(OcrEngineUnavailableError, match="пробел"):
            TesseractEngine(
                language="rus",
                tesseract_cmd=TESSERACT_CMD,
                tessdata_prefix=r"C:\Program Files\Tessdata",
            )


@requires_tesseract
class TestRealRecognition:
    def test_recognizes_printed_russian(self) -> None:
        engine = _engine()
        result = engine.recognize_page(
            render("Понятие раскрыто, факт приведён.").convert("L"), page_index=0
        )
        assert "Понятие" in result.text
        assert "раскрыто" in result.text

    def test_returns_segments_with_bbox(self) -> None:
        engine = _engine()
        result = engine.recognize_page(render("реформа 1861 года").convert("L"), page_index=0)
        assert result.segments
        for segment in result.segments:
            assert segment.bbox is not None
            assert all(0.0 <= value <= 1.0 for value in segment.bbox)
            assert result.text[segment.char_start : segment.char_end] == segment.text

    def test_confidence_is_reported(self) -> None:
        engine = _engine()
        result = engine.recognize_page(render("простой текст").convert("L"), page_index=0)
        assert result.segments
        assert all(
            segment.confidence is None or 0.0 <= segment.confidence <= 1.0
            for segment in result.segments
        )

    def test_blank_page_returns_empty(self) -> None:
        engine = _engine()
        result = engine.recognize_page(Image.new("L", (600, 300), 255), page_index=0)
        assert result.text == ""
        assert result.segments == []

    def test_empty_image_raises(self) -> None:
        engine = _engine()
        with pytest.raises(OcrEngineError):
            engine.recognize_page(Image.new("L", (0, 0)), page_index=0)

    def test_engine_does_not_mutate_input(self) -> None:
        engine = _engine()
        image = render("текст").convert("L")
        before = image.tobytes()
        engine.recognize_page(image, page_index=0)
        assert image.tobytes() == before


class TestEngineFactory:
    def test_mock_engine_is_default(self, monkeypatch) -> None:
        from app.config import settings
        from app.services.ocr.factory import build_engine

        monkeypatch.setattr(settings, "OCR_ENGINE", "mock")
        assert build_engine().name == "mock"

    def test_easyocr_reports_not_implemented(self) -> None:
        from app.services.ocr.factory import build_engine

        with pytest.raises(OcrEngineUnavailableError) as error:
            build_engine("easyocr")
        assert error.value.details["reason"] == "not_implemented"

    def test_unknown_engine_rejected(self) -> None:
        from app.services.ocr.factory import build_engine

        with pytest.raises(OcrEngineUnavailableError):
            build_engine("paddle")
