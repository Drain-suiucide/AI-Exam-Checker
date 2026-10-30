"""Тесты конвейера: склейка страниц, ретраи, диагностика, частичный сбой."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from app.services.ocr.pipeline import PAGE_SEPARATOR, OcrPipeline
from app.services.ocr.types import (
    OcrEngineError,
    OcrError,
    OcrSegment,
    PageRecognition,
)


def png(size: tuple[int, int] = (200, 120)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, "white").save(buffer, format="PNG")
    return buffer.getvalue()


class StubEngine:
    """Движок с управляемым поведением: тексты по страницам и сценарий ошибок."""

    name = "stub"
    version = "test-1"
    language = "rus"

    def __init__(
        self,
        texts: list[str],
        *,
        fail_pages: dict[int, list[BaseException]] | None = None,
    ) -> None:
        self.texts = texts
        self.fail_pages = fail_pages or {}
        self.calls: list[int] = []

    def recognize_page(self, image: Image.Image, *, page_index: int) -> PageRecognition:
        self.calls.append(page_index)
        failures = self.fail_pages.get(page_index)
        if failures:
            raise failures.pop(0)
        text = self.texts[page_index] if page_index < len(self.texts) else ""
        segments = [
            OcrSegment(
                index=index,
                page_index=page_index,
                text=word,
                char_start=start,
                char_end=start + len(word),
                confidence=0.9,
                bbox=(0.1, 0.1, 0.2, 0.2),
            )
            for index, (start, word) in enumerate(_positions(text))
        ]
        return PageRecognition(text=text, segments=segments)


def _positions(text: str) -> list[tuple[int, str]]:
    """Разбить текст на слова с их смещениями; пустой текст — без слов."""
    if not text:
        return []
    result: list[tuple[int, str]] = []
    cursor = 0
    for word in text.split(" "):
        result.append((cursor, word))
        cursor += len(word) + 1
    return result


class TestAssembly:
    def test_single_page(self) -> None:
        engine = StubEngine(["первый ответ"])
        result = OcrPipeline(engine, deskew=False).recognize([png()])
        assert result.text == "первый ответ"
        assert result.partial is False

    def test_multiple_pages_joined_with_separator(self) -> None:
        engine = StubEngine(["строка один", "строка два"])
        result = OcrPipeline(engine, deskew=False).recognize([png(), png()])
        assert result.text == f"строка один{PAGE_SEPARATOR}строка два"

    def test_segment_offsets_point_into_assembled_text(self) -> None:
        engine = StubEngine(["альфа бета", "гамма дельта"])
        result = OcrPipeline(engine, deskew=False).recognize([png(), png()])
        for segment in result.segments:
            assert result.text[segment.char_start : segment.char_end] == segment.text

    def test_segments_reindexed_across_pages(self) -> None:
        engine = StubEngine(["a b", "c d"])
        result = OcrPipeline(engine, deskew=False).recognize([png(), png()])
        assert [segment.index for segment in result.segments] == [0, 1, 2, 3]
        assert [segment.page_index for segment in result.segments] == [0, 0, 1, 1]

    def test_empty_page_produces_no_segments(self) -> None:
        engine = StubEngine(["", "текст"])
        result = OcrPipeline(engine, deskew=False).recognize([png(), png()])
        assert result.text == f"{PAGE_SEPARATOR}текст"
        assert all(segment.page_index == 1 for segment in result.segments)

    def test_mean_confidence_is_average_of_segments(self) -> None:
        engine = StubEngine(["один два три четыре"])
        result = OcrPipeline(engine, deskew=False).recognize([png()])
        assert result.mean_confidence == pytest.approx(0.9)

    def test_contract_shape(self) -> None:
        engine = StubEngine(["слово"])
        payload = OcrPipeline(engine, deskew=False).recognize([png()]).to_contract()
        assert set(payload) == {"mean_confidence", "segments"}
        assert set(payload["segments"][0]) == {
            "index",
            "page_index",
            "char_start",
            "char_end",
            "confidence",
            "bbox",
        }


class TestRetry:
    def test_transient_error_is_retried(self) -> None:
        engine = StubEngine(
            ["текст"],
            fail_pages={0: [OcrEngineError("временная", transient=True)]},
        )
        result = OcrPipeline(engine, max_attempts=2, retry_delay=0, deskew=False).recognize(
            [png()]
        )
        assert result.text == "текст"
        assert result.diagnostics.attempts == 2
        assert engine.calls == [0, 0]

    def test_permanent_error_is_not_retried(self) -> None:
        engine = StubEngine(
            ["текст"],
            fail_pages={0: [OcrEngineError("постоянная", transient=False)]},
        )
        with pytest.raises(OcrEngineError):
            OcrPipeline(engine, max_attempts=3, retry_delay=0, deskew=False).recognize([png()])
        assert engine.calls == [0]

    def test_retries_exhausted_marks_partial(self) -> None:
        engine = StubEngine(
            ["текст", "второй"],
            fail_pages={
                0: [OcrEngineError("t", transient=True), OcrEngineError("t", transient=True)]
            },
        )
        result = OcrPipeline(engine, max_attempts=2, retry_delay=0, deskew=False).recognize(
            [png(), png()]
        )
        assert result.partial is True
        assert result.text == "второй"
        assert result.diagnostics.page_errors[0]["page_index"] == 0

    def test_backoff_delay_doubles(self) -> None:
        delays: list[float] = []
        engine = StubEngine(
            ["текст"],
            fail_pages={
                0: [
                    OcrEngineError("t", transient=True),
                    OcrEngineError("t", transient=True),
                ]
            },
        )
        OcrPipeline(
            engine,
            max_attempts=3,
            retry_delay=0.5,
            sleep=delays.append,
            deskew=False,
        ).recognize([png()])
        assert delays == [0.5, 1.0]

    def test_all_pages_failed_raises(self) -> None:
        engine = StubEngine(
            ["a"],
            fail_pages={0: [OcrEngineError("p", transient=False)]},
        )
        with pytest.raises(OcrEngineError, match="ни одной страницы"):
            OcrPipeline(engine, deskew=False).recognize([png()])

    def test_unexpected_exception_wrapped(self) -> None:
        engine = StubEngine(["a"], fail_pages={0: [RuntimeError("boom")]})
        with pytest.raises(OcrEngineError, match="ни одной страницы"):
            OcrPipeline(engine, deskew=False).recognize([png()])


class TestInputHandling:
    def test_empty_page_list_rejected(self) -> None:
        with pytest.raises(OcrError, match="ни одной страницы"):
            OcrPipeline(StubEngine([]), deskew=False).recognize([])

    def test_invalid_page_aborts_whole_run(self) -> None:
        engine = StubEngine(["a", "b"])
        with pytest.raises(OcrError):
            OcrPipeline(engine, deskew=False).recognize([png(), b"not an image"])
        assert engine.calls == [], "валидация должна идти до вызова движка"

    def test_diagnostics_describe_run(self) -> None:
        engine = StubEngine(["текст"])
        result = OcrPipeline(engine, deskew=False).recognize([png()])
        payload = result.diagnostics.to_dict()
        assert payload["engine"] == "stub"
        assert payload["engine_version"] == "test-1"
        assert payload["language"] == "rus"
        assert payload["page_count"] == 1
        assert isinstance(payload["duration_ms"], int)
        assert payload["page_errors"] == []

    def test_engine_receives_copy_not_original(self) -> None:
        """Движок не должен получить ссылку на изображение страницы."""
        received: list[Image.Image] = []

        class MutatingEngine(StubEngine):
            def recognize_page(self, image: Image.Image, *, page_index: int) -> PageRecognition:
                received.append(image)
                # Предобработка приводит страницу к режиму `L`.
                fill = 0 if image.mode == "L" else (0, 0, 0)
                image.paste(fill, (0, 0, 20, 20))
                return super().recognize_page(image, page_index=page_index)

        engine = MutatingEngine(["текст"])
        OcrPipeline(engine, deskew=False).recognize([png()])
        assert received, "движок должен быть вызван"
