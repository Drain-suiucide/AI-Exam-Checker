"""Тесты синтетического набора и прогона оценки OCR."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.ocr.dataset import CATEGORIES, SAMPLES, build_dataset, write_dataset


class TestDataset:
    def test_every_sample_has_reference_text(self) -> None:
        for sample in build_dataset():
            assert sample.reference.strip(), sample.sample_id

    def test_sample_ids_are_unique(self) -> None:
        ids = [sample.sample_id for sample in build_dataset()]
        assert len(ids) == len(set(ids))

    def test_categories_match_declared_set(self) -> None:
        used = {sample.category for sample in build_dataset()}
        assert used == set(CATEGORIES)

    def test_every_category_has_at_least_two_samples(self) -> None:
        counts: dict[str, int] = {}
        for sample in build_dataset():
            counts[sample.category] = counts.get(sample.category, 0) + 1
        for category, count in counts.items():
            assert count >= 2, f"категория {category} представлена {count} образцом"

    def test_no_personal_data_markers(self) -> None:
        """В наборе не должно быть ФИО реальных частных лиц и контактов."""
        forbidden = ("@", "http://", "https://", "ул.", "тел.", "паспорт")
        for sample in build_dataset():
            lowered = sample.reference.lower()
            for marker in forbidden:
                assert marker not in lowered, f"{sample.sample_id}: {marker}"

    def test_generation_is_deterministic(self) -> None:
        first = build_dataset(seed=42)
        second = build_dataset(seed=42)
        for left, right in zip(first, second, strict=True):
            assert left.reference == right.reference
            assert left.png_bytes() == right.png_bytes()

    def test_different_seeds_change_degradations(self) -> None:
        rotated_a = [s for s in build_dataset(seed=1) if s.category == "rotated"]
        rotated_b = [s for s in build_dataset(seed=2) if s.category == "rotated"]
        assert [s.png_bytes() for s in rotated_a] != [s.png_bytes() for s in rotated_b]

    def test_degradations_match_category(self) -> None:
        """`printed` и `mixed` — контрольные группы без деградаций.

        `mixed` проверяет распознавание цифр, дат и имён, поэтому его нельзя
        смешивать с искажениями: иначе непонятно, что именно сломалось.
        """
        for sample in build_dataset():
            if sample.category in ("printed", "mixed", "handwriting_font"):
                assert sample.degradations == (), sample.sample_id
            else:
                assert sample.degradations, sample.sample_id

    def test_images_are_valid_png(self) -> None:
        for sample in build_dataset():
            data = sample.png_bytes()
            assert data.startswith(b"\x89PNG\r\n\x1a\n"), sample.sample_id

    def test_critical_entities_are_inside_reference(self) -> None:
        for spec in SAMPLES:
            for term, _kind in spec.critical_entities:
                assert term in spec.reference, f"{spec.sample_id}: {term}"


class TestManifest:
    def test_written_manifest_describes_samples(self, tmp_path: Path) -> None:
        path = write_dataset(tmp_path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["version"] == 1
        assert len(payload["samples"]) == len(SAMPLES)
        assert set(payload["categories"]) == set(CATEGORIES)

    def test_manifest_entries_have_license_and_reference(self, tmp_path: Path) -> None:
        path = write_dataset(tmp_path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        for entry in payload["samples"]:
            assert entry["license"].startswith("synthetic")
            assert entry["reference"]
            assert (tmp_path / entry["file"]).exists()

    def test_manifest_reference_matches_image_name(self, tmp_path: Path) -> None:
        path = write_dataset(tmp_path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        for entry in payload["samples"]:
            assert entry["file"] == f"{entry['sample_id']}.png"


@pytest.mark.skipif(
    not pytest.importorskip("PIL"),
    reason="Pillow обязателен",
)
def test_sample_renders_with_cyrillic() -> None:
    sample = build_dataset()[0]
    assert sample.image.width > 0
    assert sample.image.height > 0
    # Изображение не пустое: на белом фоне есть тёмные пиксели текста.
    grayscale = sample.image.convert("L")
    assert grayscale.getextrema()[0] < 128
