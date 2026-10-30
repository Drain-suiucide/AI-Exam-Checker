"""Движок Tesseract 5 через `pytesseract`.

Особенности реализации:
- координаты приводятся к нормализованным (0..1) от размера страницы, как
  требует API_CONTRACT §2.3;
- `char_start`/`char_end` считаются по фактически собранному тексту, поэтому
  всегда консистентны с `Transcription.text`;
- слова с `conf < 0` (Tesseract не распознал) отбрасываются, но не «додумываются»;
- ошибки движка классифицируются на временные и постоянные: конвейер ретраит
  только временные.
"""

from __future__ import annotations

import logging
import os
import shutil
import unicodedata
from pathlib import Path

from PIL import Image

from app.services.ocr.types import (
    OcrEngineError,
    OcrEngineUnavailableError,
    OcrSegment,
    PageRecognition,
)

logger = logging.getLogger(__name__)

#: Параметры сегментации. `--psm 6` («единый блок текста») выбран по замерам
#: на собственном наборе: CER 1.7% против 6.1% у `--psm 3/4` и 4.3% у `--psm 11`
#: (см. docs/evaluation/ocr_evaluation.md). Это типичный случай для ответа,
#: написанного на бланке одним блоком.
DEFAULT_CONFIG = "--psm 6"

#: Слова, разделённые пробелом; перевод строки — между строками Tesseract.
_NEWLINE = "\n"
_SPACE = " "


class TesseractEngine:
    """Обёртка над `pytesseract.image_to_data`."""

    name = "tesseract"

    def __init__(
        self,
        *,
        language: str = "rus",
        tesseract_cmd: str | None = None,
        tessdata_prefix: str | None = None,
        config: str = DEFAULT_CONFIG,
    ) -> None:
        try:
            import pytesseract
        except ImportError as exc:  # pragma: no cover - зависит от окружения
            raise OcrEngineUnavailableError(
                "Модуль pytesseract не установлен.",
                details={"hint": "uv add pytesseract"},
            ) from exc

        self._pytesseract = pytesseract
        self.language = language

        cmd = tesseract_cmd or os.environ.get("TESSERACT_CMD")
        if cmd:
            pytesseract.pytesseract.tesseract_cmd = cmd
        else:
            found = shutil.which("tesseract")
            if found:
                pytesseract.pytesseract.tesseract_cmd = found

        # `--tessdata-dir` передаётся в config каждого вызова: так модель можно
        # держать в каталоге проекта, не трогая системный `tessdata`.
        # Переменная TESSDATA_PREFIX здесь не используется намеренно — она
        # перебивает аргумент командной строки и делает поведение неявным.
        #
        # Кавычки не ставим: pytesseract разбирает config через shlex с
        # posix=False на Windows и оставляет кавычки частью пути. Путь с
        # пробелами поэтому не поддерживается — сообщаем об этом явно.
        if tessdata_prefix:
            prefix_path = Path(tessdata_prefix).as_posix()
            if " " in prefix_path:
                raise OcrEngineUnavailableError(
                    "Путь к каталогу моделей не должен содержать пробелов.",
                    details={"tessdata_prefix": prefix_path},
                )
            self._tessdata_arg = f"--tessdata-dir {prefix_path}"
            config = f"{config} {self._tessdata_arg}"
        else:
            self._tessdata_arg = ""
        self._config = config.strip()

        self.version = self._detect_version()

    def _detect_version(self) -> str:
        try:
            raw = str(self._pytesseract.get_tesseract_version())
        except Exception as exc:  # noqa: BLE001 - любая ошибка = движок недоступен
            raise OcrEngineUnavailableError(
                "Tesseract не найден или не запускается.",
                details={"hint": "Установите Tesseract 5 и укажите TESSERACT_CMD"},
            ) from exc
        return raw.splitlines()[0].strip() if raw else "unknown"

    def ensure_available(self) -> None:
        """Проверить, что движок установлен и нужный язык загружен."""
        try:
            # `--tessdata-dir` обязателен: без него Tesseract смотрит только в
            # системный каталог и не увидит модель из проекта.
            languages = self._pytesseract.get_languages(config=self._tessdata_arg)
        except Exception as exc:  # noqa: BLE001
            raise OcrEngineUnavailableError(
                "Не удалось получить список языков Tesseract.",
            ) from exc
        # Tesseract принимает несколько моделей через «+» (например, `rus+eng`):
        # каждую нужно найти отдельно.
        missing = [name for name in self.language.split("+") if name not in languages]
        if missing:
            raise OcrEngineUnavailableError(
                f"Языковая модель '{', '.join(missing)}' не найдена.",
                details={
                    "language": self.language,
                    "missing": missing,
                    "available": languages,
                    "hint": "Скачайте *.traineddata в OCR_TESSDATA_PREFIX",
                },
            )

    def recognize_page(self, image: Image.Image, *, page_index: int) -> PageRecognition:
        width, height = image.size
        if width == 0 or height == 0:
            raise OcrEngineError(
                "Пустое изображение страницы.",
                details={"page_index": page_index},
            )

        try:
            data = self._pytesseract.image_to_data(
                image,
                lang=self.language,
                config=self._config,
                output_type=self._pytesseract.Output.DICT,
            )
        except self._pytesseract.TesseractNotFoundError as exc:
            raise OcrEngineUnavailableError(
                "Tesseract не найден.",
                details={"hint": "Укажите TESSERACT_CMD"},
            ) from exc
        except self._pytesseract.TesseractError as exc:
            # Ошибка бинарника: чаще всего это нехватка памяти или таймаут
            # (временные), реже — повреждённый ввод (постоянная).
            transient = any(
                marker in str(exc).lower()
                for marker in ("memory", "timeout", "resource temporarily unavailable")
            )
            raise OcrEngineError(
                "Tesseract не смог обработать страницу.",
                details={"page_index": page_index, "reason": str(exc)},
                transient=transient,
            ) from exc

        return _recognition_from_data(data, page_index=page_index, width=width, height=height)


def _recognition_from_data(
    data: dict[str, list],
    *,
    page_index: int,
    width: int,
    height: int,
) -> PageRecognition:
    """Собрать текст и сегменты с консистентными смещениями.

    Текст собирается здесь же, по тем же правилам, по которым считаются
    смещения, поэтому `char_start`/`char_end` всегда указывают в `text`.
    Пустые блоки и слова с отрицательной уверенностью пропускаются.
    """
    pieces: list[str] = []
    segments: list[OcrSegment] = []
    cursor = 0
    previous_line: tuple[int, int, int] | None = None
    previous_paragraph: tuple[int, int] | None = None
    index = 0

    texts = data.get("text", [])
    for position, raw_text in enumerate(texts):
        text = str(raw_text).strip()
        if not text:
            continue

        confidence_raw = data["conf"][position]
        try:
            confidence_value = float(confidence_raw)
        except (TypeError, ValueError):
            confidence_value = -1.0
        # Tesseract отдаёт -1 для служебных строк; такие слова не текст.
        if confidence_value < 0:
            continue

        page_num = int(data["page_num"][position])
        block_num = int(data["block_num"][position])
        paragraph = (page_num, int(data["par_num"][position]))
        line = (block_num, paragraph[1], int(data["line_num"][position]))

        if previous_line is None:
            separator = ""
        elif line != previous_line:
            separator = _NEWLINE if paragraph != previous_paragraph else _SPACE
        else:
            separator = _SPACE

        if separator:
            pieces.append(separator)
            cursor += len(separator)

        char_start = cursor
        cursor += len(text)
        char_end = cursor
        pieces.append(text)

        left = int(data["left"][position])
        top = int(data["top"][position])
        word_width = int(data["width"][position])
        word_height = int(data["height"][position])
        bbox = (
            round(left / width, 6),
            round(top / height, 6),
            round(min(1.0, (left + word_width) / width), 6),
            round(min(1.0, (top + word_height) / height), 6),
        )

        segments.append(
            OcrSegment(
                index=index,
                page_index=page_index,
                text=text,
                char_start=char_start,
                char_end=char_end,
                # Tesseract даёт 0..100; приводим к 0..1 как в контракте.
                confidence=round(confidence_value / 100.0, 4),
                bbox=bbox,
            )
        )
        index += 1
        previous_line = line
        previous_paragraph = paragraph

    return PageRecognition(
        text=_normalize_text("".join(pieces)),
        segments=segments,
    )


def _normalize_text(text: str) -> str:
    """Привести текст к виду, который требует контракт.

    API_CONTRACT §2.3: `text` — NFC, переводы строк `\\n`. Tesseract может
    вернуть `\\r\\n` на Windows и разрозненные варианты Unicode, поэтому
    нормализация обязательна — иначе `char_count` и `text_sha256` будут
    зависеть от платформы.
    """
    normalized = unicodedata.normalize("NFC", text)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.strip()


def default_engine(
    *,
    language: str = "rus",
    tesseract_cmd: str | None = None,
    tessdata_prefix: str | Path | None = None,
) -> TesseractEngine:
    """Собрать движок с настройками по умолчанию из окружения."""
    return TesseractEngine(
        language=language,
        tesseract_cmd=tesseract_cmd,
        tessdata_prefix=str(tessdata_prefix) if tessdata_prefix else None,
    )
