"""Метрики качества OCR: CER, WER и ошибки в критичных сущностях.

Метрики считаются по расстоянию Левенштейна на уровне символов и слов.
Сознательные ограничения (см. docs/evaluation/ocr_evaluation.md):

- регистр и пунктуация не нормализуются: для истории «Пётр» и «пётр» — не
  одно и то же, а запятая в дате меняет смысл. Нормализация только для
  отдельного «мягкого» режима, если он явно запрошен;
- CER на коротких эталонах шумный: одна ошибка в 20 символах даёт 5%;
  поэтому отчёт всегда содержит абсолютные числа ошибок;
- агрегирование по корпусу — по сумме правок, а не среднее CER по образцам:
  иначе короткие строки доминируют.
"""

from __future__ import annotations

from dataclasses import dataclass


def edit_distance(reference: str, hypothesis: str) -> int:
    """Расстояние Левенштейна (вставки, удаления, замены).

    Две строки памяти вместо матрицы: для страниц по 10 тыс. символов
    матрица была бы 100 МБ.
    """
    if reference == hypothesis:
        return 0
    if not reference:
        return len(hypothesis)
    if not hypothesis:
        return len(reference)

    previous = list(range(len(hypothesis) + 1))
    for i, ref_char in enumerate(reference, start=1):
        current = [i]
        for j, hyp_char in enumerate(hypothesis, start=1):
            cost = 0 if ref_char == hyp_char else 1
            current.append(
                min(
                    previous[j] + 1,  # удаление
                    current[j - 1] + 1,  # вставка
                    previous[j - 1] + cost,  # замена
                )
            )
        previous = current
    return previous[-1]


@dataclass(frozen=True, slots=True)
class ErrorRate:
    """CER или WER: доля правок от длины эталона."""

    edits: int
    reference_length: int

    @property
    def rate(self) -> float:
        if self.reference_length == 0:
            return 0.0 if self.edits == 0 else 1.0
        return self.edits / self.reference_length

    def __str__(self) -> str:
        return f"{self.rate:.4f} ({self.edits}/{self.reference_length})"


def character_error_rate(reference: str, hypothesis: str) -> ErrorRate:
    """CER = расстояние Левенштейна / длина эталона в символах."""
    return ErrorRate(edit_distance(reference, hypothesis), len(reference))


def word_error_rate(reference: str, hypothesis: str) -> ErrorRate:
    """WER = расстояние Левенштейна по словам / число слов эталона."""
    ref_words = reference.split()
    hyp_words = hypothesis.split()
    return ErrorRate(_word_edit_distance(ref_words, hyp_words), len(ref_words))


def _word_edit_distance(reference: list[str], hypothesis: list[str]) -> int:
    if reference == hypothesis:
        return 0
    if not reference:
        return len(hypothesis)
    if not hypothesis:
        return len(reference)

    previous = list(range(len(hypothesis) + 1))
    for i, ref_word in enumerate(reference, start=1):
        current = [i]
        for j, hyp_word in enumerate(hypothesis, start=1):
            cost = 0 if ref_word == hyp_word else 1
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost))
        previous = current
    return previous[-1]


@dataclass(frozen=True, slots=True)
class EntityCheck:
    """Сохранность одной критичной сущности в распознанном тексте."""

    term: str
    kind: str
    preserved: bool
    #: Наиболее похожий фрагмент гипотезы, если сущность потеряна.
    nearest: str | None = None


def _normalize_for_match(text: str) -> str:
    """Сравнение сущностей без учёта регистра и ё/е.

    Только для проверки сохранности: «Пётр» и «Петр» — одна сущность.
    Основные CER/WER считаются без этой нормализации.
    """
    return text.casefold().replace("ё", "е")


def _nearest_window(term: str, hypothesis: str) -> str | None:
    """Найти в гипотезе окно той же длины с минимальным расстоянием.

    Нужно, чтобы в отчёте было видно, во что превратилась сущность
    («Александр II» → «Александр П»), а не только факт потери.
    """
    normalized_hypothesis = _normalize_for_match(hypothesis)
    normalized_term = _normalize_for_match(term)
    length = len(normalized_term)
    if length == 0 or len(normalized_hypothesis) < length:
        return None

    best: tuple[int, str] | None = None
    step = max(1, length // 4)
    for start in range(0, len(normalized_hypothesis) - length + 1, step):
        window = normalized_hypothesis[start : start + length]
        distance = edit_distance(normalized_term, window)
        if best is None or distance < best[0]:
            best = (distance, hypothesis[start : start + length])
            if distance == 0:
                break
    return best[1] if best else None


def check_entities(
    hypothesis: str,
    entities: tuple[tuple[str, str], ...],
) -> list[EntityCheck]:
    """Проверить, сохранились ли критичные сущности в распознанном тексте."""
    normalized = _normalize_for_match(hypothesis)
    checks: list[EntityCheck] = []
    for term, kind in entities:
        preserved = _normalize_for_match(term) in normalized
        checks.append(
            EntityCheck(
                term=term,
                kind=kind,
                preserved=preserved,
                nearest=None if preserved else _nearest_window(term, hypothesis),
            )
        )
    return checks
