"""Тесты метрик CER/WER и проверки критичных сущностей."""

from __future__ import annotations

import pytest

from app.services.ocr.metrics import (
    ErrorRate,
    character_error_rate,
    check_entities,
    edit_distance,
    word_error_rate,
)


class TestEditDistance:
    @pytest.mark.parametrize(
        ("left", "right", "expected"),
        [
            ("", "", 0),
            ("абв", "абв", 0),
            ("абв", "абг", 1),      # замена
            ("абв", "аб", 1),       # удаление
            ("аб", "абв", 1),       # вставка
            ("", "абв", 3),
            ("абв", "", 3),
            ("кот", "ток", 2),
            ("Александр II", "Александр П", 2),  # одна «I» удалена, вторая заменена
        ],
    )
    def test_known_distances(self, left: str, right: str, expected: int) -> None:
        assert edit_distance(left, right) == expected

    def test_is_symmetric(self) -> None:
        assert edit_distance("реформа", "реформы") == edit_distance("реформы", "реформа")

    def test_long_strings_do_not_blow_up_memory(self) -> None:
        left = "а" * 5000
        right = "а" * 4999 + "б"
        assert edit_distance(left, right) == 1


class TestErrorRate:
    def test_rate_is_edits_over_reference_length(self) -> None:
        rate = ErrorRate(edits=2, reference_length=40)
        assert rate.rate == pytest.approx(0.05)
        assert str(rate) == "0.0500 (2/40)"

    def test_empty_reference_with_no_edits(self) -> None:
        assert ErrorRate(0, 0).rate == 0.0

    def test_empty_reference_with_edits(self) -> None:
        # Вся вставка считается ошибкой: делить не на что.
        assert ErrorRate(3, 0).rate == 1.0


class TestCharacterErrorRate:
    def test_perfect_recognition(self) -> None:
        text = "Понятие раскрыто."
        result = character_error_rate(text, text)
        assert result.edits == 0
        assert result.rate == 0.0

    def test_roman_numeral_loss_is_counted(self) -> None:
        # «II» → «П»: одна «I» удалена, вторая заменена кириллической «П».
        result = character_error_rate("Александр II", "Александр П")
        assert result.edits == 2
        assert result.reference_length == 12
        assert result.rate == pytest.approx(2 / 12)

    def test_case_difference_counts_as_error(self) -> None:
        """Регистр не нормализуется: для имён это значимая разница."""
        assert character_error_rate("Пётр", "пётр").edits == 1

    def test_yo_and_ye_are_different_characters(self) -> None:
        assert character_error_rate("провёл", "провел").edits == 1

    def test_transposition_counts_as_two_edits(self) -> None:
        # Расстояние Левенштейна не считает перестановку одной правкой.
        assert character_error_rate("кот", "ток").edits == 2


class TestWordErrorRate:
    def test_perfect_recognition(self) -> None:
        text = "реформа 1861 года"
        assert word_error_rate(text, text).rate == 0.0

    def test_one_wrong_word(self) -> None:
        result = word_error_rate("Александр II провёл реформу", "Александр П провёл реформу")
        assert result.edits == 1
        assert result.reference_length == 4
        assert result.rate == pytest.approx(0.25)

    def test_whitespace_is_collapsed_for_words(self) -> None:
        # WER по словам не должен наказывать за переносы строк.
        assert word_error_rate("одно два", "одно\nдва").edits == 0

    def test_empty_reference(self) -> None:
        assert word_error_rate("", "").rate == 0.0
        assert word_error_rate("", "лишнее").rate == 1.0


class TestEntityChecks:
    ENTITIES = (
        ("Александр II", "name"),
        ("1861", "date"),
        ("не отменил", "negation"),
        ("крепостное право", "term"),
    )

    def test_all_preserved(self) -> None:
        text = "Александр II не отменил крепостное право в 1861 году."
        checks = check_entities(text, self.ENTITIES)
        assert all(check.preserved for check in checks)

    def test_lost_entity_reports_nearest_fragment(self) -> None:
        text = "Александр П не отменил крепостное право в 1861 году."
        checks = {check.term: check for check in check_entities(text, self.ENTITIES)}
        assert checks["Александр II"].preserved is False
        assert checks["Александр II"].nearest is not None
        assert "Александр" in checks["Александр II"].nearest

    def test_negation_loss_is_detected(self) -> None:
        text = "Александр II отменил крепостное право в 1861 году."
        checks = {check.term: check for check in check_entities(text, self.ENTITIES)}
        assert checks["не отменил"].preserved is False

    def test_case_and_yo_are_ignored_for_entities(self) -> None:
        """Сохранность сущности проверяется мягче, чем CER."""
        text = "александр ii не отменил крепостное право в 1861 году"
        checks = check_entities(text, self.ENTITIES)
        assert all(check.preserved for check in checks)

    def test_nearest_is_none_when_hypothesis_too_short(self) -> None:
        checks = check_entities("коротко", (("очень длинная сущность", "term"),))
        assert checks[0].preserved is False
        assert checks[0].nearest is None

    def test_kind_is_preserved_in_result(self) -> None:
        checks = check_entities("1861", (("1861", "date"),))
        assert checks[0].kind == "date"
