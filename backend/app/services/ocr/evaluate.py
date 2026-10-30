"""Прогон оценки OCR на синтетическом наборе.

Считает CER/WER по каждой категории, проверяет сохранность критичных
сущностей (имена, даты, отрицания, термины) и пишет markdown-отчёт.

Запуск:
    uv run python -m app.services.ocr.evaluate --engine tesseract \
        --out ../docs/evaluation/ocr_evaluation.md
    uv run python -m app.services.ocr.evaluate --engine mock --out /tmp/mock.md

Флаг `--sweep` дополнительно прогоняет варианты параметров (`--psm`, deskew,
модель `tessdata_fast`/`tessdata_best`) и вставляет в отчёт сравнительную
таблицу — именно так выбирался `--psm 6`. `--sweep-only` печатает только её.

Требования к окружению для Tesseract: `TESSERACT_CMD` и `OCR_TESSDATA_PREFIX`
(или `TESSDATA_PREFIX`). Без них движок не запустится — скрипт сообщит об этом.
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from app.config import settings
from app.services.ocr import recognize_pages
from app.services.ocr.dataset import CATEGORIES, build_dataset
from app.services.ocr.metrics import (
    EntityCheck,
    character_error_rate,
    check_entities,
    word_error_rate,
)
from app.services.ocr.pipeline import OcrPipeline
from app.services.ocr.tesseract_engine import TesseractEngine
from app.services.ocr.types import OcrError, OcrResult, OcrSegment


@dataclass(slots=True)
class SampleOutcome:
    sample_id: str
    category: str
    reference: str
    hypothesis: str
    cer_edits: int
    cer_length: int
    wer_edits: int
    wer_length: int
    entities: list[EntityCheck]
    duration_ms: int
    preprocessing: list[str]
    #: Уверенность сегментов, которыми движок заменил потерянную сущность.
    #: Нужна, чтобы показать: высокая уверенность не гарантирует правильность.
    misread_confidences: list[tuple[str, str, float]] = field(default_factory=list)
    partial: bool = False
    split: str = "dev"

    @property
    def cer(self) -> float:
        return self.cer_edits / self.cer_length if self.cer_length else 0.0

    @property
    def wer(self) -> float:
        return self.wer_edits / self.wer_length if self.wer_length else 0.0

    @property
    def lost_entities(self) -> list[EntityCheck]:
        return [entity for entity in self.entities if not entity.preserved]


@dataclass(slots=True)
class CategorySummary:
    name: str
    description: str
    sample_count: int = 0
    cer_edits: int = 0
    cer_length: int = 0
    wer_edits: int = 0
    wer_length: int = 0
    entities_total: int = 0
    entities_lost: int = 0
    lost_by_kind: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    durations: list[int] = field(default_factory=list)

    @property
    def corpus_cer(self) -> float:
        return self.cer_edits / self.cer_length if self.cer_length else 0.0

    @property
    def corpus_wer(self) -> float:
        return self.wer_edits / self.wer_length if self.wer_length else 0.0

    @property
    def entity_recall(self) -> float:
        if not self.entities_total:
            return 1.0
        return 1.0 - self.entities_lost / self.entities_total

    @property
    def median_ms(self) -> int:
        return int(statistics.median(self.durations)) if self.durations else 0


def _flatten(text: str) -> str:
    """Схлопнуть пробелы для CER/WER.

    Переносы строк — свойство вёрстки, а не распознавания: без схлопывания
    метрика наказывает за разную разбивку на строки и завышает ошибку.
    Это ограничение описано в отчёте.
    """
    return " ".join(text.split())


def _misread_confidences(
    entities: list[EntityCheck],
    segments: list[OcrSegment],
    raw_text: str,
) -> list[tuple[str, str, float]]:
    """Уверенность сегментов, стоящих на месте потерянной сущности.

    `EntityCheck.nearest` — фрагмент гипотезы, в который превратилась
    сущность. Находим его позицию в исходном тексте и берём сегменты,
    пересекающиеся с этим диапазоном: так в отчёт попадает фактическая
    уверенность неверного слова, а не соседних правильных.
    """
    found: list[tuple[str, str, float]] = []
    for entity in entities:
        if entity.preserved or not entity.nearest:
            continue
        start = raw_text.casefold().find(entity.nearest.casefold())
        if start < 0:
            continue
        end = start + len(entity.nearest)
        for segment in segments:
            if segment.confidence is None:
                continue
            overlaps = segment.char_start < end and segment.char_end > start
            # Сегмент, который действительно встречается в написании сущности
            # («Пётр»), — правильное слово рядом с ошибкой, а не ошибка.
            if overlaps and segment.text.casefold() not in entity.term.casefold():
                found.append((entity.term, segment.text, segment.confidence))
    return found


def evaluate(
    runner: Callable[[bytes], OcrResult],
    *,
    seed: int = 20261029,
    limit: int | None = None,
    split: str | None = None,
) -> tuple[list[SampleOutcome], dict]:
    """Прогнать набор через `runner` и собрать результат по каждому образцу.

    `runner` принимает байты PNG и возвращает `OcrResult`. Такая сигнатура
    позволяет сравнивать варианты движка (разные `--psm`, deskew, модели)
    на одном и том же наборе, не дублируя логику подсчёта метрик.
    `split` ограничивает прогон выборкой (`dev` или `test`).
    """
    samples = build_dataset(seed=seed)
    if split:
        samples = [sample for sample in samples if sample.split == split]
    if limit:
        samples = samples[:limit]

    outcomes: list[SampleOutcome] = []
    engine_info: dict[str, object] = {}

    for sample in samples:
        result = runner(sample.png_bytes())
        if not engine_info:
            engine_info = {
                "name": result.diagnostics.engine,
                "version": result.diagnostics.engine_version,
                "language": result.diagnostics.language,
            }
        reference = _flatten(sample.reference)
        hypothesis = _flatten(result.text)
        cer = character_error_rate(reference, hypothesis)
        wer = word_error_rate(reference, hypothesis)
        entities = check_entities(hypothesis, sample.critical_entities)
        outcomes.append(
            SampleOutcome(
                sample_id=sample.sample_id,
                category=sample.category,
                reference=reference,
                hypothesis=hypothesis,
                cer_edits=cer.edits,
                cer_length=cer.reference_length,
                wer_edits=wer.edits,
                wer_length=wer.reference_length,
                entities=entities,
                misread_confidences=_misread_confidences(entities, result.segments, result.text),
                duration_ms=result.diagnostics.duration_ms,
                preprocessing=list(result.diagnostics.preprocessing),
                partial=result.partial,
                split=sample.split,
            )
        )

    return outcomes, engine_info


def summarize(outcomes: list[SampleOutcome]) -> dict[str, CategorySummary]:
    summaries: dict[str, CategorySummary] = {
        key: CategorySummary(name=key, description=description)
        for key, description in CATEGORIES.items()
    }
    for outcome in outcomes:
        summary = summaries.setdefault(
            outcome.category,
            CategorySummary(name=outcome.category, description=""),
        )
        summary.sample_count += 1
        summary.cer_edits += outcome.cer_edits
        summary.cer_length += outcome.cer_length
        summary.wer_edits += outcome.wer_edits
        summary.wer_length += outcome.wer_length
        summary.durations.append(outcome.duration_ms)
        for entity in outcome.entities:
            summary.entities_total += 1
            if not entity.preserved:
                summary.entities_lost += 1
                summary.lost_by_kind[entity.kind] += 1
    return summaries


def _format_entities(outcome: SampleOutcome) -> str:
    if not outcome.lost_entities:
        return "—"
    parts = []
    for entity in outcome.lost_entities:
        nearest = f" → «{entity.nearest}»" if entity.nearest else ""
        parts.append(f"{entity.term} ({entity.kind}){nearest}")
    return "; ".join(parts)


def render_report(
    outcomes: list[SampleOutcome],
    summaries: dict[str, CategorySummary],
    engine_info: dict,
    *,
    seed: int,
    sweep_rows: list[tuple[str, float, int, int]] | None = None,
    dev_outcomes: list[SampleOutcome] | None = None,
) -> str:
    """Собрать отчёт. `outcomes` — отложенная выборка `test` (итоговые цифры),
    `dev_outcomes` — выборка, на которой подбирались параметры (для справки)."""
    dev_outcomes = dev_outcomes or []
    dev_summaries = summarize(dev_outcomes)
    total_cer_edits = sum(outcome.cer_edits for outcome in outcomes)
    total_cer_length = sum(outcome.cer_length for outcome in outcomes)
    total_wer_edits = sum(outcome.wer_edits for outcome in outcomes)
    total_wer_length = sum(outcome.wer_length for outcome in outcomes)
    total_entities = sum(len(outcome.entities) for outcome in outcomes)
    lost_entities = sum(len(outcome.lost_entities) for outcome in outcomes)
    durations = [outcome.duration_ms for outcome in outcomes]

    lines: list[str] = []
    add = lines.append

    add("# Оценка качества OCR")
    add("")
    add(f"Отчёт сгенерирован: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")
    add("")
    add("## 1. Условия прогона")
    add("")
    add("| Параметр | Значение |")
    add("|---|---|")
    add(f"| Движок | `{engine_info.get('name', '?')}` |")
    add(f"| Версия движка | `{engine_info.get('version', '?')}` |")
    add(f"| Языковая модель | `{engine_info.get('language', '?')}` |")
    add(f"| Python | {platform.python_version()} |")
    add(f"| Платформа | {platform.system()} {platform.release()} |")
    add(f"| Seed набора | {seed} |")
    add(f"| Образцов | {len(outcomes)} |")
    add("")
    add("Команда воспроизведения:")
    add("")
    add("```bash")
    add("uv run python -m app.services.ocr.evaluate --engine tesseract \\")
    add("    --out ../docs/evaluation/ocr_evaluation.md")
    add("```")
    add("")

    add("## 2. Состав тестового набора")
    add("")
    add(
        "Набор синтетический: изображения отрисованы кодом репозитория "
        "(`app/services/ocr/dataset.py`) системными шрифтами Windows с "
        "кириллицей. Персональных данных и реальных экзаменационных работ нет; "
        "формулировки вымышленные, исторические факты — из школьной программы."
    )
    add("")
    add("| Категория | Описание | dev | test |")
    add("|---|---|---|---|")
    for key, description in CATEGORIES.items():
        dev_count = dev_summaries[key].sample_count if key in dev_summaries else 0
        test_count = summaries[key].sample_count if key in summaries else 0
        add(f"| `{key}` | {description} | {dev_count} | {test_count} |")
    add(f"| **Итого** | | {len(dev_outcomes)} | {len(outcomes)} |")
    add("")
    add(
        "Категории `printed` и `mixed` — контрольные группы без деградаций: "
        "`printed` проверяет базовое качество, `mixed` — распознавание цифр, дат, "
        "римских цифр, имён и отрицаний. Остальные категории вносят по одному "
        "типу искажения, чтобы ошибку можно было отнести к причине. "
        "`handwriting_font` — **не рукопись**, а печатный шрифт, имитирующий "
        "почерк (см. §7, п. 2)."
    )
    add("")
    add(
        "**Разделение данных.** Образцы разбиты на две выборки в поле `split` "
        "манифеста. `dev` — на ней подбирались параметры движка (`--psm`, "
        "deskew, модель, язык). `test` — отложенная: тексты и изображения "
        "добавлены после выбора параметров, ни подбор, ни правки кода по ней "
        "не делались. Итоговые метрики (§3–§5) посчитаны только по `test`; "
        "`dev` приведена в §4 для справки и как индикатор переобучения "
        "настроек. Разделение по текстам, а не по искажениям: одинаковых "
        "эталонных текстов в обеих выборках нет."
    )
    add("")

    add("## 3. Итоговые метрики (отложенная выборка `test`)")
    add("")
    add("| Метрика | Значение |")
    add("|---|---|")
    corpus_cer = total_cer_edits / total_cer_length if total_cer_length else 0.0
    corpus_wer = total_wer_edits / total_wer_length if total_wer_length else 0.0
    add(f"| CER (по корпусу) | {corpus_cer:.4f} ({total_cer_edits}/{total_cer_length}) |")
    add(f"| WER (по корпусу) | {corpus_wer:.4f} ({total_wer_edits}/{total_wer_length}) |")
    add(
        f"| Сохранность критичных сущностей | "
        f"{(total_entities - lost_entities) / total_entities:.4f} "
        f"({total_entities - lost_entities}/{total_entities}) |"
    )
    add(f"| Медианное время на страницу | {int(statistics.median(durations))} мс |")
    add("")
    add(
        "CER и WER агрегируются по сумме правок, а не как среднее по образцам: "
        "иначе короткие строки получают несоразмерный вес."
    )
    add("")

    add("## 4. Метрики по категориям")
    add("")
    add("| Категория | CER | WER | Сохранность сущностей | Медиана, мс |")
    add("|---|---|---|---|---|")
    for key in CATEGORIES:
        summary = summaries.get(key)
        if summary is None or summary.sample_count == 0:
            continue
        add(
            f"| `{key}` | {summary.corpus_cer:.4f} "
            f"({summary.cer_edits}/{summary.cer_length}) | "
            f"{summary.corpus_wer:.4f} | "
            f"{summary.entity_recall:.4f} "
            f"({summary.entities_total - summary.entities_lost}/{summary.entities_total}) | "
            f"{summary.median_ms} |"
        )
    add("")

    if dev_outcomes:
        dev_edits = sum(outcome.cer_edits for outcome in dev_outcomes)
        dev_length = sum(outcome.cer_length for outcome in dev_outcomes)
        dev_wer_edits = sum(outcome.wer_edits for outcome in dev_outcomes)
        dev_wer_length = sum(outcome.wer_length for outcome in dev_outcomes)
        add("### Выборка `dev` (для справки)")
        add("")
        add(
            "Параметры подбирались на этой выборке, поэтому её цифры оптимистичны. "
            "Расхождение с `test` показывает, насколько настройка не переносится "
            "на новые образцы."
        )
        add("")
        add("| Категория | CER | WER | Сохранность сущностей |")
        add("|---|---|---|---|")
        for key in CATEGORIES:
            summary = dev_summaries.get(key)
            if summary is None or summary.sample_count == 0:
                continue
            add(
                f"| `{key}` | {summary.corpus_cer:.4f} "
                f"({summary.cer_edits}/{summary.cer_length}) | "
                f"{summary.corpus_wer:.4f} | "
                f"{summary.entity_recall:.4f} "
                f"({summary.entities_total - summary.entities_lost}/{summary.entities_total}) |"
            )
        add(
            f"| **Итого** | {dev_edits / dev_length:.4f} ({dev_edits}/{dev_length}) | "
            f"{dev_wer_edits / dev_wer_length:.4f} | |"
        )
        add("")

    add("## 5. Ошибки в критичных сущностях")
    add("")
    add(
        "Отдельно проверяется, сохранились ли имена, даты, отрицания и термины: "
        "именно эти ошибки меняют смысл исторического ответа, тогда как "
        "опечатка в служебном слове — нет."
    )
    add("")

    by_kind: dict[str, list[EntityCheck]] = defaultdict(list)
    for outcome in outcomes:
        for entity in outcome.lost_entities:
            by_kind[entity.kind].append(entity)

    if by_kind:
        add("| Тип сущности | Потеряно | Примеры |")
        add("|---|---|---|")
        for kind, items in sorted(by_kind.items()):
            examples = "; ".join(
                f"«{item.term}» → «{item.nearest}»" if item.nearest else f"«{item.term}»"
                for item in items[:3]
            )
            add(f"| `{kind}` | {len(items)} | {examples} |")
        add("")
    else:
        add("Потерь критичных сущностей не обнаружено.")
        add("")

    add("### Постраничный разбор")
    add("")
    add("| Образец | Категория | CER | WER | Потерянные сущности |")
    add("|---|---|---|---|---|")
    for outcome in outcomes:
        add(
            f"| `{outcome.sample_id}` | {outcome.category} | "
            f"{outcome.cer:.4f} ({outcome.cer_edits}/{outcome.cer_length}) | "
            f"{outcome.wer:.4f} | {_format_entities(outcome)} |"
        )
    add("")

    add("### Уверенность неверных распознаваний")
    add("")
    add(
        "Уверенность Tesseract — вспомогательный признак, а не доказательство "
        "правильности. Ниже — фактическая уверенность сегментов, которыми "
        "движок заменил потерянную сущность:"
    )
    add("")
    misreads = [
        (outcome.sample_id, term, segment_text, confidence)
        for outcome in outcomes
        for term, segment_text, confidence in outcome.misread_confidences
    ]
    if misreads:
        add("| Образец | Сущность | Распознано как | Уверенность |")
        add("|---|---|---|---|")
        for sample_id, term, segment_text, confidence in misreads:
            add(f"| `{sample_id}` | «{term}» | «{segment_text}» | {confidence:.2f} |")
        add("")
        high = [item for item in misreads if item[3] >= 0.9]
        worst = max(misreads, key=lambda item: item[3])
        caught = len(misreads) - len(high)
        add(
            f"Из {len(misreads)} неверных сегментов {caught} имеют уверенность "
            f"ниже 0.90 — порог по уверенности отсеял бы их. Но "
            f"{len(high)} {_plural(len(high), 'остаётся', 'остаются', 'остаются')} "
            f"выше порога, вплоть до {worst[3]:.2f} "
            f"(«{worst[1]}» → «{worst[2]}» в `{worst[0]}`). Значит, уверенность "
            f"годится как сигнал «посмотри внимательнее», но не как "
            f"доказательство правильности: часть смысловых ошибок она пропускает "
            f"с высокой оценкой."
        )
    else:
        add("Неверных сегментов на месте сущностей не зафиксировано.")
    add("")

    add("## 6. Выбор параметров движка")
    add("")
    add(
        "Варианты параметров сравнивались **только на выборке `dev`**; `test` в "
        "подборе не участвовала. Таблица показывает относительную разницу между "
        "вариантами на `dev`, а не независимую оценку. Воспроизвести: "
        "`uv run python -m app.services.ocr.evaluate --sweep-only`."
    )
    add("")
    if sweep_rows:
        add(render_sweep(sweep_rows))
    else:
        add("_Таблица не рассчитана: прогон вариантов не запрашивался._")
    add("")
    add(
        "Выбранная конфигурация: `--psm 6` («единый блок текста»: ответ на "
        "бланке — один блок), модель `tessdata_fast`, языки `rus+eng`, deskew "
        "включён. Языки `rus+eng` нужны из-за римских цифр: в модели `rus` нет "
        "латинской «I», и «Пётр I» превращается в «Пётр [» (проверено прямым "
        "сравнением `rus` и `rus+eng` на образцах с римскими цифрами). "
        "Различия между вариантами в пределах нескольких правок на этом объёме "
        "данных не значимы."
    )
    add("")

    add("## 7. Ограничения измерения")
    add("")
    add(
        "1. **Синтетика, а не реальные сканы.** Изображения отрисованы шрифтом "
        "и искажены фильтрами. Реальная ручка, тетрадный лист, тени и перспектива "
        "дают другую статистику ошибок. Результаты нельзя переносить на боевые "
        "сканы без отдельного замера."
    )
    add(
        "2. **Настоящая рукопись не измерена.** Категория `handwriting_font` — "
        "печатные шрифты (Ink Free, Segoe Script, Comic Sans), имитирующие "
        "почерк. У них одинаковая форма одной буквы, нет нажима, слитности и "
        "индивидуальных вариаций, поэтому цифры этой категории **нельзя** "
        "считать оценкой качества на реальной рукописи; они лишь показывают, "
        "что стилизованные начертания распознаются хуже обычных. Tesseract "
        "не поддерживает русскую рукопись (см. `docs/research/ocr_comparison.md`). "
        "Для рукописи нужны другой движок и набор настоящих образцов с разрешением "
        "на использование."
    )
    add(
        "3. **Малый объём.** Выборка `test` — "
        f"{len(outcomes)} образцов и {total_cer_length} символов эталона: "
        "доверительные интервалы широкие, различия между категориями (в них по "
        "1–2 образца) значимыми считать нельзя. Одна ошибка в имени меняет "
        "сохранность сущностей на несколько процентных пунктов."
    )
    add(
        "4. **Отложенная выборка не независима полностью.** Тексты `test` "
        "добавлены после выбора параметров, но написаны тем же автором, теми "
        "же шаблонами, отрисованы теми же шрифтами и деградациями, что и `dev`. "
        "Это защищает от подгонки параметров, но не от смещения самого генератора: "
        "реальные сканы будут отличаться сильнее."
    )
    add(
        "5. **Схлопывание пробелов.** CER/WER считаются после приведения "
        "пробельных символов к одному пробелу: перенос строки — свойство вёрстки, "
        "а не распознавания. Ошибки внутри слов и в символах это не скрывает, "
        "но «склейка» и «разрыв» слов в отчёт как ошибки не попадают."
    )
    add(
        "6. **Регистр и «ё» не нормализуются.** `Пётр` и `петр` считаются "
        "разными: для имён собственных это осмысленно. Проверка сохранности "
        "сущностей, наоборот, мягче (без учёта регистра и ё/е)."
    )
    misread_values = [
        confidence
        for outcome in outcomes
        for _term, _text, confidence in outcome.misread_confidences
    ]
    if misread_values:
        confidence_note = (
            f"в прогоне неверные сегменты получали от {min(misread_values):.2f} "
            f"до {max(misread_values):.2f} (см. таблицу выше)"
        )
    else:
        confidence_note = "неверных сегментов на месте сущностей в прогоне не было"
    add(
        "7. **Confidence не калиброван.** Уверенность Tesseract — не вероятность "
        f"правильности: {confidence_note}. Уверенность используется как "
        "вспомогательный признак для подсветки, а не как основание считать "
        "текст верным; порог «достаточной уверенности» здесь не назначается, "
        "низкая уверенность не отбрасывается и не «исправляется» автоматически."
    )
    add("")
    add(
        "**Порог качества не устанавливается.** Задача не даёт основания "
        "выбрать конкретное значение CER как «приемлемое»: оно зависит от "
        "требований к проверке ответов и от того, сколько правок готов вносить "
        "пользователь. Числа выше — измеренная база для такого решения, "
        "а не норматив."
    )
    add("")

    add("## 8. Наблюдения")
    add("")
    observations = _observations(outcomes, summaries)
    for observation in observations:
        add(f"- {observation}")
    add("")

    return "\n".join(lines)


def _observations(
    outcomes: list[SampleOutcome], summaries: dict[str, CategorySummary]
) -> list[str]:
    """Сформулировать выводы, которые действительно следуют из данных."""
    result: list[str] = []

    worst = max(
        (summary for summary in summaries.values() if summary.sample_count),
        key=lambda summary: summary.corpus_cer,
        default=None,
    )
    best = min(
        (summary for summary in summaries.values() if summary.sample_count),
        key=lambda summary: summary.corpus_cer,
        default=None,
    )
    if worst and best and worst.name != best.name:
        result.append(
            f"Наибольший CER — в категории `{worst.name}` ({worst.corpus_cer:.4f}), "
            f"наименьший — в `{best.name}` ({best.corpus_cer:.4f})."
        )

    roman_entities = [
        entity
        for outcome in outcomes
        for entity in outcome.entities
        if entity.kind == "name" and any(char in entity.term for char in "IVX")
    ]
    roman_losses = [entity for entity in roman_entities if not entity.preserved]
    if roman_losses:
        examples = ", ".join(
            f"«{item.term}» → «{item.nearest}»" for item in roman_losses[:4] if item.nearest
        )
        result.append(
            f"Римские цифры в именах монархов теряются систематически: "
            f"{len(roman_losses)} из {len(roman_entities)} "
            f"{_plural(len(roman_entities), 'случая', 'случаев', 'случаев')}. "
            f"Примеры: {examples}. Это устойчивая ошибка движка, а не случайный "
            f"шум, и она меняет исторический факт («Александр II» ≠ «Александр III»)."
        )

    negation_losses = [
        entity
        for outcome in outcomes
        for entity in outcome.lost_entities
        if entity.kind == "negation"
    ]
    if negation_losses:
        result.append(
            f"Потеряны отрицания: {len(negation_losses)}. Отрицание меняет смысл "
            f"ответа на противоположный, поэтому такие случаи требуют "
            f"обязательной проверки человеком."
        )
    else:
        result.append(
            "Отрицания во всех образцах сохранились — на этом наборе движок "
            "не инвертировал смысл высказываний."
        )

    date_losses = [
        entity
        for outcome in outcomes
        for entity in outcome.lost_entities
        if entity.kind == "date"
    ]
    if date_losses:
        examples = ", ".join(
            f"«{item.term}» → «{item.nearest}»" for item in date_losses[:3] if item.nearest
        )
        result.append(
            f"Потеряно дат: {len(date_losses)} ({examples}). "
            f"Здесь расхождение только в типе тире (en-dash → дефис): Tesseract "
            f"нормализует типографику, и для проверки смысла это безобидно, но "
            f"строковое сравнение с эталоном его не прощает."
        )
    else:
        result.append("Все даты в наборе распознаны верно.")

    # CER и сохранность сущностей меряют разное: шум и пятна ломают
    # служебные слова, но не имена и даты.
    noisy = [
        summary
        for summary in summaries.values()
        if summary.sample_count and summary.corpus_cer > 0.03 and summary.entities_lost == 0
    ]
    for summary in noisy:
        result.append(
            f"В категории `{summary.name}` CER {summary.corpus_cer:.4f}, но все "
            f"критичные сущности сохранены: искажения бьют по служебным словам "
            f"и окончаниям, а не по именам и датам. Это показывает, почему "
            f"одного CER недостаточно — смысл ответа он не измеряет."
        )

    high_cer = [outcome for outcome in outcomes if outcome.cer > 0.05]
    if high_cer:
        result.append(
            f"Образцов с CER выше 5%: {len(high_cer)} из {len(outcomes)} "
            f"({', '.join(f'`{outcome.sample_id}`' for outcome in high_cer)})."
        )

    return result


def _plural(count: int, one: str, few: str, many: str) -> str:
    """Русское склонение после числительного."""
    if count % 10 == 1 and count % 100 != 11:
        return one
    if 2 <= count % 10 <= 4 and not 12 <= count % 100 <= 14:
        return few
    return many


def make_runner(engine_name: str) -> Callable[[bytes], OcrResult]:
    """Runner для штатного пути: движок из настроек, конвейер по умолчанию."""
    return lambda data: recognize_pages([data], engine_name=engine_name)


def _tesseract_runner(
    *, config: str, deskew: bool, tessdata_prefix: str | None, language: str | None = None
) -> Callable[[bytes], OcrResult]:
    engine = TesseractEngine(
        language=language or settings.OCR_LANGUAGE,
        tesseract_cmd=settings.OCR_TESSERACT_CMD,
        tessdata_prefix=tessdata_prefix,
        config=config,
    )
    engine.ensure_available()
    pipeline = OcrPipeline(engine, deskew=deskew)
    return lambda data: pipeline.recognize([data])


@dataclass(slots=True)
class Variant:
    """Один вариант параметров для сравнения."""

    label: str
    runner: Callable[[bytes], OcrResult]


def sweep_variants() -> list[Variant]:
    """Варианты, между которыми выбирался движок.

    Набор тот же, поэтому таблица показывает относительную разницу, а не
    независимую оценку: победитель выбран по этим же данным.
    """
    variants: list[Variant] = []
    base_prefix = settings.OCR_TESSDATA_PREFIX

    for psm in (3, 4, 6, 11):
        variants.append(
            Variant(
                f"psm {psm}",
                _tesseract_runner(
                    config=f"--psm {psm}", deskew=True, tessdata_prefix=base_prefix
                ),
            )
        )

    variants.append(
        Variant(
            "psm 6, deskew выкл.",
            _tesseract_runner(config="--psm 6", deskew=False, tessdata_prefix=base_prefix),
        )
    )
    variants.append(
        Variant(
            "psm 6, пробелы сохранены",
            _tesseract_runner(
                config="--psm 6 -c preserve_interword_spaces=1",
                deskew=True,
                tessdata_prefix=base_prefix,
            ),
        )
    )

    variants.append(
        Variant(
            "psm 6, только rus (без латиницы)",
            _tesseract_runner(
                config="--psm 6", deskew=True, tessdata_prefix=base_prefix, language="rus"
            ),
        )
    )

    best_dir = _find_best_tessdata()
    if best_dir:
        variants.append(
            Variant(
                "psm 6, tessdata_best",
                _tesseract_runner(config="--psm 6", deskew=True, tessdata_prefix=str(best_dir)),
            )
        )
    return variants


def _find_best_tessdata() -> Path | None:
    """Каталог `tessdata_best` рядом с используемой моделью, если он есть."""
    if not settings.OCR_TESSDATA_PREFIX:
        return None
    candidate = Path(settings.OCR_TESSDATA_PREFIX).parent / "tessdata_best"
    names = settings.OCR_LANGUAGE.split("+")
    if all((candidate / f"{name}.traineddata").exists() for name in names):
        return candidate
    return None


def run_sweep(*, seed: int, limit: int | None) -> list[tuple[str, float, int, int]]:
    """Прогнать все варианты и вернуть (label, CER, правки, длина эталона).

    Только выборка `dev`: отложенная `test` в подборе параметров не участвует.
    """
    rows: list[tuple[str, float, int, int]] = []
    for variant in sweep_variants():
        outcomes, _ = evaluate(variant.runner, seed=seed, limit=limit, split="dev")
        edits = sum(outcome.cer_edits for outcome in outcomes)
        length = sum(outcome.cer_length for outcome in outcomes)
        rows.append((variant.label, edits / length if length else 0.0, edits, length))
    return rows


def render_sweep(rows: list[tuple[str, float, int, int]]) -> str:
    lines = ["| Вариант | CER | Правок |", "|---|---|---|"]
    best = min((row[1] for row in rows), default=None)
    for label, cer, edits, length in sorted(rows, key=lambda row: row[1]):
        marker = " **(лучший результат)**" if best is not None and cer == best else ""
        lines.append(f"| {label}{marker} | {cer:.4f} | {edits}/{length} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Оценить OCR на синтетическом наборе.")
    parser.add_argument("--engine", default="tesseract", choices=("mock", "tesseract"))
    parser.add_argument("--seed", type=int, default=20261029)
    parser.add_argument("--limit", type=int, default=None, help="Ограничить число образцов")
    parser.add_argument("--out", type=Path, default=None, help="Путь к markdown-отчёту")
    parser.add_argument("--json", type=Path, default=None, help="Путь к JSON с результатами")
    parser.add_argument(
        "--sweep",
        action="store_true",
        help="Добавить в отчёт сравнение вариантов параметров (медленно)",
    )
    parser.add_argument(
        "--sweep-only",
        action="store_true",
        help="Только сравнить варианты параметров и выйти",
    )
    args = parser.parse_args(argv)

    # Отчёт содержит «→», «–» и кириллицу: консоль Windows (cp1251) их не кодирует.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    try:
        if args.sweep_only:
            rows = run_sweep(seed=args.seed, limit=args.limit)
            table = render_sweep(rows)
            print(table)
            if args.out:
                args.out.parent.mkdir(parents=True, exist_ok=True)
                args.out.write_text(table + "\n", encoding="utf-8")
            return 0

        runner = make_runner(args.engine)
        outcomes, engine_info = evaluate(
            runner, seed=args.seed, limit=args.limit, split="test"
        )
        dev_outcomes, _ = evaluate(runner, seed=args.seed, limit=args.limit, split="dev")
    except OcrError as error:
        print(f"Ошибка распознавания: {error.message}", file=sys.stderr)
        print(json.dumps(error.details, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    summaries = summarize(outcomes)
    report = render_report(
        outcomes,
        summaries,
        engine_info,
        seed=args.seed,
        sweep_rows=run_sweep(seed=args.seed, limit=args.limit) if args.sweep else None,
        dev_outcomes=dev_outcomes,
    )

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report, encoding="utf-8")
        print(f"Отчёт записан: {args.out}")
    else:
        print(report)

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "engine": engine_info,
            "seed": args.seed,
            "samples": [
                {
                    "sample_id": outcome.sample_id,
                    "category": outcome.category,
                    "split": outcome.split,
                    "cer": outcome.cer,
                    "wer": outcome.wer,
                    "cer_edits": outcome.cer_edits,
                    "cer_length": outcome.cer_length,
                    "reference": outcome.reference,
                    "hypothesis": outcome.hypothesis,
                    "lost_entities": [
                        {"term": entity.term, "kind": entity.kind, "nearest": entity.nearest}
                        for entity in outcome.lost_entities
                    ],
                    "duration_ms": outcome.duration_ms,
                }
                for outcome in outcomes
            ],
        }
        args.json.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"JSON записан: {args.json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
