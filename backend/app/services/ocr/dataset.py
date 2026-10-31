"""Генератор синтетического тестового набора для оценки OCR.

Набор строится из шаблонных текстов, нарисованных системными шрифтами
Windows, и деградаций, имитирующих реальные условия съёмки. Персональных
данных нет: все тексты — вымышленные формулировки в стиле ответов ЕГЭ по
истории, а имена/даты взяты из школьной программы.

Категории (по типу сложности) совпадают с требованием задачи:
`printed` — чистый печатный; `low_light` — низкий контраст/темнота;
`rotated` — наклон; `low_res` — низкое разрешение; `smudges` — пятна и
зачёркивания; `mixed` — цифры, даты, имена, отрицания.

Каждый элемент набора — `Sample` с эталонной транскрипцией и метаданными.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

#: Шрифты с полной кириллицей, поставляемые с Windows.
_FONT_CANDIDATES = (
    (r"C:\Windows\Fonts\times.ttf", "Times New Roman"),
    (r"C:\Windows\Fonts\arial.ttf", "Arial"),
    (r"C:\Windows\Fonts\calibri.ttf", "Calibri"),
    (r"C:\Windows\Fonts\segoeui.ttf", "Segoe UI"),
)

#: Категории набора: ключ -> человекочитаемое описание.
CATEGORIES: dict[str, str] = {
    "printed": "Чистый печатный текст, белый фон, ровные строки",
    "low_light": "Низкий контраст: серый текст на сером фоне, тусклое освещение",
    "rotated": "Наклон листа на 2–4 градуса",
    "low_res": "Низкое разрешение: мелкий шрифт и даунскейл",
    "smudges": "Пятна, шум и зачёркивания поверх текста",
    "mixed": "Смешанный: цифры, даты, римские цифры, имена, отрицания",
    "handwriting_font": (
        "Прокси рукописи: шрифт, имитирующий почерк. НЕ настоящая рукопись, "
        "см. ограничения в отчёте"
    ),
}

#: Выборки набора. `dev` — на ней разрешено подбирать параметры движка;
#: `test` — отложенная: по ней считается итоговая метрика, параметры по ней
#: не настраиваются.
SPLITS: tuple[str, ...] = ("dev", "test")

#: Шрифты, имитирующие почерк (все содержат полную кириллицу).
_HANDWRITING_FONTS = (
    (r"C:\Windows\Fonts\Inkfree.ttf", "Ink Free"),
    (r"C:\Windows\Fonts\segoesc.ttf", "Segoe Script"),
    (r"C:\Windows\Fonts\comic.ttf", "Comic Sans MS"),
)


@dataclass(frozen=True, slots=True)
class SampleText:
    """Текст образца: эталон + метки критичных сущностей."""

    sample_id: str
    category: str
    reference: str
    #: Сущности, ошибки в которых критичны: имена, даты, отрицания, термины.
    critical_entities: tuple[tuple[str, str], ...] = ()
    #: Выборка: `dev` (настройка параметров) или `test` (отложенная).
    split: str = "dev"

    @property
    def critical_terms(self) -> tuple[str, ...]:
        return tuple(term for term, _kind in self.critical_entities)


@dataclass(frozen=True, slots=True)
class Sample:
    """Готовый образец: изображение и эталон."""

    sample_id: str
    category: str
    reference: str
    image: Image.Image
    critical_entities: tuple[tuple[str, str], ...] = ()
    font_name: str = ""
    font_size: int = 0
    render_width: int = 0
    render_height: int = 0
    degradations: tuple[str, ...] = field(default_factory=tuple)
    split: str = "dev"

    def png_bytes(self) -> bytes:
        import io

        buffer = io.BytesIO()
        self.image.save(buffer, format="PNG")
        return buffer.getvalue()


#: Образцы текстов. Формулировки вымышленные, факты — из школьной программы.
SAMPLES: tuple[SampleText, ...] = (
    SampleText(
        sample_id="printed-01",
        category="printed",
        reference=(
            "Понятие «реформа» означает изменение в общественной жизни, "
            "проводимое властью. Пример: реформа 1861 года отменила "
            "крепостное право в России."
        ),
        critical_entities=(("1861", "date"), ("крепостное право", "term")),
    ),
    SampleText(
        sample_id="printed-02",
        category="printed",
        reference=(
            "Пётр I основал Санкт-Петербург в 1703 году. "
            "Полтавская битва произошла в 1709 году и укрепила положение России."
        ),
        critical_entities=(
            ("Пётр I", "name"),
            ("Санкт-Петербург", "name"),
            ("1703", "date"),
            ("1709", "date"),
        ),
    ),
    SampleText(
        sample_id="printed-03",
        category="printed",
        reference=(
            "Александр II провёл земскую реформу. "
            "Александр III не отменил реформы предшественника, но ограничил их."
        ),
        critical_entities=(
            ("Александр II", "name"),
            ("Александр III", "name"),
            ("не отменил", "negation"),
        ),
    ),
    SampleText(
        sample_id="printed-04",
        category="printed",
        reference=(
            "Внешняя политика СССР в 1930-е годы была направлена на "
            "создание системы коллективной безопасности в Европе."
        ),
        critical_entities=(("1930-е", "date"), ("коллективной безопасности", "term")),
    ),
    SampleText(
        sample_id="printed-05",
        category="printed",
        reference=(
            "Куликовская битва состоялась в 1380 году. Дмитрий Донской возглавил русское войско."
        ),
        critical_entities=(
            ("1380", "date"),
            ("Дмитрий Донской", "name"),
        ),
    ),
    SampleText(
        sample_id="low-light-01",
        category="low_light",
        reference=(
            "Отмена крепостного права в 1861 году стала поворотным событием в истории России."
        ),
        critical_entities=(("1861", "date"), ("крепостного права", "term")),
    ),
    SampleText(
        sample_id="low-light-02",
        category="low_light",
        reference=(
            "Новгородская республика существовала до 1478 года, когда её присоединил Иван III."
        ),
        critical_entities=(
            ("1478", "date"),
            ("Иван III", "name"),
        ),
    ),
    SampleText(
        sample_id="low-light-03",
        category="low_light",
        reference=(
            "Столыпинская аграрная реформа началась в 1906 году "
            "и не решила всех проблем крестьянства."
        ),
        critical_entities=(
            ("1906", "date"),
            ("не решила", "negation"),
        ),
    ),
    SampleText(
        sample_id="rotated-01",
        category="rotated",
        reference=(
            "Бородинское сражение произошло в 1812 году. Русской армией командовал Михаил Кутузов."
        ),
        critical_entities=(
            ("1812", "date"),
            ("Михаил Кутузов", "name"),
        ),
    ),
    SampleText(
        sample_id="rotated-02",
        category="rotated",
        reference=(
            "Первый съезд РСДРП состоялся в 1898 году в Минске. Партия не имела единой программы."
        ),
        critical_entities=(
            ("1898", "date"),
            ("не имела", "negation"),
        ),
    ),
    SampleText(
        sample_id="rotated-03",
        category="rotated",
        reference=(
            "Екатерина II взошла на престол в 1762 году. "
            "При ней была присоединена Крымская область."
        ),
        critical_entities=(
            ("Екатерина II", "name"),
            ("1762", "date"),
        ),
    ),
    SampleText(
        sample_id="low-res-01",
        category="low_res",
        reference=(
            "Первый пятилетний план был принят в 1928 году. "
            "Индустриализация требовала больших ресурсов."
        ),
        critical_entities=(("1928", "date"), ("Индустриализация", "term")),
    ),
    SampleText(
        sample_id="low-res-02",
        category="low_res",
        reference=(
            "Невская битва произошла в 1240 году. Александр Невский возглавил новгородское войско."
        ),
        critical_entities=(
            ("1240", "date"),
            ("Александр Невский", "name"),
        ),
    ),
    SampleText(
        sample_id="low-res-03",
        category="low_res",
        reference=(
            "Манифест о вольности дворянства издала Елизавета Петровна "
            "в 1762 году, но его отменил Пётр III."
        ),
        critical_entities=(
            ("Елизавета Петровна", "name"),
            ("1762", "date"),
            ("Пётр III", "name"),
        ),
    ),
    SampleText(
        sample_id="smudges-01",
        category="smudges",
        reference=(
            "Гражданская война в России завершилась в 1922 году. "
            "Белое движение потерпело поражение."
        ),
        critical_entities=(("1922", "date"), ("потерпело поражение", "term")),
    ),
    SampleText(
        sample_id="smudges-02",
        category="smudges",
        reference=(
            "Ленд-лиз был важным источником поставок для СССР в годы Великой Отечественной войны."
        ),
        critical_entities=(("Ленд-лиз", "term"), ("Великой Отечественной", "term")),
    ),
    SampleText(
        sample_id="smudges-03",
        category="smudges",
        reference=("Соборное уложение 1649 года окончательно закрепило крепостное право в России."),
        critical_entities=(("1649", "date"), ("крепостное право", "term")),
    ),
    SampleText(
        sample_id="mixed-01",
        category="mixed",
        reference=(
            "В 1703 году Пётр I основал город. В 1712 году столица "
            "была перенесена из Москвы в Санкт-Петербург."
        ),
        critical_entities=(
            ("1703", "date"),
            ("1712", "date"),
            ("Пётр I", "name"),
            ("Санкт-Петербург", "name"),
        ),
    ),
    SampleText(
        sample_id="mixed-02",
        category="mixed",
        reference=(
            "Николай II отрёкся от престола 2 марта 1917 года. "
            "Временное правительство не смогло удержать власть."
        ),
        critical_entities=(
            ("Николай II", "name"),
            ("2 марта 1917", "date"),
            ("не смогло", "negation"),
        ),
    ),
    SampleText(
        sample_id="mixed-03",
        category="mixed",
        reference=(
            "В 1941–1945 годах СССР вёл войну против Германии. "
            "Сталинградская битва стала переломом."
        ),
        critical_entities=(
            ("1941–1945", "date"),
            ("Сталинградская битва", "term"),
        ),
    ),
    SampleText(
        sample_id="mixed-04",
        category="mixed",
        reference=(
            "Александр I не поддержал континентальную блокаду "
            "после 1812 года, что обострило отношения с Францией."
        ),
        critical_entities=(
            ("Александр I", "name"),
            ("не поддержал", "negation"),
            ("1812", "date"),
        ),
    ),
    # --- Прокси рукописи (dev): шрифт-имитация почерка, не настоящая рукопись ---
    SampleText(
        sample_id="handwriting-font-01",
        category="handwriting_font",
        reference=("Пётр I провёл реформу армии. Рекрутские наборы начались в 1705 году."),
        critical_entities=(("Пётр I", "name"), ("1705", "date")),
    ),
    SampleText(
        sample_id="handwriting-font-02",
        category="handwriting_font",
        reference=(
            "Екатерина II не отменила крепостное право. "
            "Пугачёвское восстание произошло в 1773 году."
        ),
        critical_entities=(
            ("Екатерина II", "name"),
            ("не отменила", "negation"),
            ("1773", "date"),
        ),
    ),
    SampleText(
        sample_id="handwriting-font-03",
        category="handwriting_font",
        reference=("Смута закончилась избранием Михаила Романова в 1613 году."),
        critical_entities=(("Михаила Романова", "name"), ("1613", "date")),
    ),
    # --- Отложенная выборка (test): по ней параметры не настраивались ---
    SampleText(
        sample_id="test-printed-01",
        category="printed",
        split="test",
        reference=(
            "Иван IV принял царский титул в 1547 году. "
            "Опричнина не укрепила государство, а ослабила его."
        ),
        critical_entities=(
            ("Иван IV", "name"),
            ("1547", "date"),
            ("не укрепила", "negation"),
        ),
    ),
    SampleText(
        sample_id="test-printed-02",
        category="printed",
        split="test",
        reference=(
            "Крымская война закончилась Парижским миром в 1856 году. "
            "Россия потеряла право держать флот на Чёрном море."
        ),
        critical_entities=(("1856", "date"), ("Парижским миром", "term")),
    ),
    SampleText(
        sample_id="test-low-light-01",
        category="low_light",
        split="test",
        reference=(
            "Александр II подписал манифест 19 февраля 1861 года. "
            "Реформа не дала крестьянам полной свободы."
        ),
        critical_entities=(
            ("Александр II", "name"),
            ("19 февраля 1861", "date"),
            ("не дала", "negation"),
        ),
    ),
    SampleText(
        sample_id="test-rotated-01",
        category="rotated",
        split="test",
        reference=(
            "Пётр III правил недолго и был свергнут в 1762 году. К власти пришла Екатерина II."
        ),
        critical_entities=(
            ("Пётр III", "name"),
            ("1762", "date"),
            ("Екатерина II", "name"),
        ),
    ),
    SampleText(
        sample_id="test-low-res-01",
        category="low_res",
        split="test",
        reference=(
            "Ледовое побоище состоялось в 1242 году. "
            "Александр Невский разбил рыцарей Ливонского ордена."
        ),
        critical_entities=(
            ("1242", "date"),
            ("Александр Невский", "name"),
        ),
    ),
    SampleText(
        sample_id="test-smudges-01",
        category="smudges",
        split="test",
        reference=(
            "Декабристы выступили на Сенатской площади в 1825 году. "
            "Восстание не удалось и было подавлено."
        ),
        critical_entities=(
            ("1825", "date"),
            ("не удалось", "negation"),
        ),
    ),
    SampleText(
        sample_id="test-mixed-01",
        category="mixed",
        split="test",
        reference=(
            "Николай I правил с 1825 по 1855 год. "
            "Николай II не смог сохранить империю после 1917 года."
        ),
        critical_entities=(
            ("Николай I", "name"),
            ("1825", "date"),
            ("1855", "date"),
            ("Николай II", "name"),
            ("не смог", "negation"),
            ("1917", "date"),
        ),
    ),
    SampleText(
        sample_id="test-mixed-02",
        category="mixed",
        split="test",
        reference=(
            "Павел I издал указ о престолонаследии в 1797 году. "
            "Александр III не изменил этот порядок."
        ),
        critical_entities=(
            ("Павел I", "name"),
            ("1797", "date"),
            ("Александр III", "name"),
            ("не изменил", "negation"),
        ),
    ),
    SampleText(
        sample_id="test-handwriting-font-01",
        category="handwriting_font",
        split="test",
        reference=(
            "Иван III освободил Русь от ордынской зависимости в 1480 году. "
            "Стояние на Угре обошлось без битвы."
        ),
        critical_entities=(
            ("Иван III", "name"),
            ("1480", "date"),
            ("без битвы", "negation"),
        ),
    ),
    SampleText(
        sample_id="test-handwriting-font-02",
        category="handwriting_font",
        split="test",
        reference=(
            "Пётр I не поддержал заговор царевны Софьи. Стрелецкий бунт был подавлен в 1698 году."
        ),
        critical_entities=(
            ("Пётр I", "name"),
            ("не поддержал", "negation"),
            ("1698", "date"),
        ),
    ),
)


def _pick_font(
    size: int,
    *,
    rng: random.Random,
    preferred: str | None = None,
    pool: tuple[tuple[str, str], ...] = _FONT_CANDIDATES,
) -> ImageFont.FreeTypeFont:
    """Выбрать системный шрифт с кириллицей из `pool`."""
    candidates = list(pool)
    if preferred:
        candidates.sort(key=lambda item: item[1] != preferred)
    rng.shuffle(candidates)
    for path, _name in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    raise RuntimeError(
        "Не найден шрифт с поддержкой кириллицы. Ожидались системные шрифты Windows."
    )


def _wrap(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Разбить текст на строки по ширине с учётом реальных метрик шрифта."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if font.getlength(candidate) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _render(
    text: str,
    *,
    font: ImageFont.FreeTypeFont,
    line_height: int,
    margin: int,
    width: int,
    background: tuple[int, int, int] = (255, 255, 255),
    foreground: tuple[int, int, int] = (20, 20, 20),
) -> Image.Image:
    """Нарисовать текст на изображении заданной ширины."""
    lines = _wrap(text, font, width - 2 * margin)
    height = margin * 2 + line_height * len(lines)
    image = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(image)
    for index, line in enumerate(lines):
        draw.text((margin, margin + index * line_height), line, font=font, fill=foreground)
    return image


def _noise_layer(size: tuple[int, int], *, rng: random.Random, amplitude: int) -> Image.Image:
    """Слой шума на `random.Random`, чтобы генерация была воспроизводимой.

    `Image.effect_noise` использует глобальный генератор Pillow и даёт разный
    результат при каждом запуске — для детерминированного набора это не годится.
    """
    pixels = bytes(rng.randrange(256) for _ in range(size[0] * size[1]))
    layer = Image.frombytes("L", size, pixels)
    # Сжимаем динамический диапазон вокруг среднего: amplitude задаёт «силу» шума.
    return layer.point(lambda value: 128 + (value - 128) * amplitude // 255)


def _degrade_low_light(
    image: Image.Image, *, rng: random.Random
) -> tuple[Image.Image, tuple[str, ...]]:
    """Имитировать тусклое освещение: низкий контраст и лёгкий шум."""
    from PIL import ImageEnhance

    steps = ["low_contrast", "darken"]
    result = ImageEnhance.Contrast(image).enhance(0.45)
    result = ImageEnhance.Brightness(result).enhance(0.75)
    # Шум «соль-перец» — характерный для съёмки при плохом свете.
    noise = _noise_layer(result.size, rng=rng, amplitude=60)
    result = Image.blend(result.convert("L"), noise, alpha=0.06).convert("RGB")
    steps.append("noise")
    return result, tuple(steps)


def _degrade_rotated(
    image: Image.Image, *, rng: random.Random
) -> tuple[Image.Image, tuple[str, ...]]:
    """Повернуть лист на малый угол, как при съёмке без штатива."""
    angle = rng.uniform(2.0, 4.0) * rng.choice((-1, 1))
    rotated = image.rotate(
        angle,
        resample=Image.Resampling.BICUBIC,
        fillcolor=(255, 255, 255),
        expand=True,
    )
    return rotated, (f"rotate_{angle:+.1f}deg",)


def _degrade_low_res(
    image: Image.Image, *, rng: random.Random
) -> tuple[Image.Image, tuple[str, ...]]:
    """Уменьшить разрешение, как при съёмке слабой камерой."""
    width, height = image.size
    scale = rng.uniform(0.45, 0.55)
    small = image.resize(
        (max(1, int(width * scale)), max(1, int(height * scale))),
        Image.Resampling.BILINEAR,
    )
    return small, (f"downscale_x{scale:.2f}",)


def _degrade_smudges(
    image: Image.Image, *, rng: random.Random
) -> tuple[Image.Image, tuple[str, ...]]:
    """Добавить пятна, зачёркивание и зернистость.

    Зачёркивание имитирует исправление в работе: оно не должно удалять текст,
    а только усложнять распознавание.
    """
    result = image.convert("RGB")
    draw = ImageDraw.Draw(result)
    width, height = result.size

    for _ in range(3):
        x = rng.randint(0, width - 1)
        y = rng.randint(0, height - 1)
        radius = rng.randint(6, max(8, width // 40))
        draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            fill=(90, 90, 90),
        )

    # Зачёркивание поперёк средней строки.
    strike_y = rng.randint(height // 3, max(height // 3 + 1, 2 * height // 3))
    draw.line(
        (int(width * 0.05), strike_y, int(width * 0.45), strike_y + rng.randint(-4, 4)),
        fill=(30, 30, 30),
        width=max(2, height // 200),
    )

    noise = _noise_layer(result.size, rng=rng, amplitude=45)
    result = Image.blend(result, noise.convert("RGB"), alpha=0.04)
    return result, ("blobs", "strikethrough", "grain")


def build_sample(spec: SampleText, *, seed: int) -> Sample:
    """Отрисовать образец и применить деградации его категории."""
    rng = random.Random(seed)
    # `mixed` и `printed` рендерим крупнее: важно проверить сам текст,
    # а не устойчивость к деградациям.
    font_size = 30 if spec.category in ("printed", "mixed") else 28
    pool = _HANDWRITING_FONTS if spec.category == "handwriting_font" else _FONT_CANDIDATES
    font = _pick_font(font_size, rng=rng, pool=pool)
    line_height = int(font_size * 1.6)
    width = 1000

    image = _render(spec.reference, font=font, line_height=line_height, margin=40, width=width)
    degradations: tuple[str, ...] = ()

    if spec.category == "low_light":
        image, degradations = _degrade_low_light(image, rng=rng)
    elif spec.category == "rotated":
        image, degradations = _degrade_rotated(image, rng=rng)
    elif spec.category == "low_res":
        image, degradations = _degrade_low_res(image, rng=rng)
    elif spec.category == "smudges":
        image, degradations = _degrade_smudges(image, rng=rng)

    return Sample(
        sample_id=spec.sample_id,
        category=spec.category,
        reference=spec.reference,
        image=image,
        critical_entities=spec.critical_entities,
        split=spec.split,
        font_name=getattr(font, "path", ""),
        font_size=font_size,
        render_width=width,
        render_height=image.size[1],
        degradations=degradations,
    )


def build_dataset(seed: int = 20261029) -> list[Sample]:
    """Собрать полный набор образцов (детерминированно по `seed`)."""
    return [build_sample(spec, seed=seed + index) for index, spec in enumerate(SAMPLES)]


def write_dataset(target: Path, *, seed: int = 20261029) -> Path:
    """Записать набор на диск: PNG + `manifest.json` с эталонами."""
    target.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = []

    for sample in build_dataset(seed=seed):
        filename = f"{sample.sample_id}.png"
        sample.image.save(target / filename, format="PNG")
        manifest.append(
            {
                "sample_id": sample.sample_id,
                "category": sample.category,
                "split": sample.split,
                "file": filename,
                "reference": sample.reference,
                "critical_entities": [
                    {"term": term, "kind": kind} for term, kind in sample.critical_entities
                ],
                "font_name": sample.font_name,
                "font_size": sample.font_size,
                "render_width": sample.render_width,
                "render_height": sample.render_height,
                "degradations": list(sample.degradations),
                "license": "synthetic, generated by this repository",
            }
        )

    manifest_path = target / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "version": 1,
                "seed": seed,
                "categories": CATEGORIES,
                "splits": list(SPLITS),
                "note": (
                    "Синтетические изображения: персональных данных нет, "
                    "тексты вымышленные. Шрифты — системные, изображения "
                    "сгенерированы кодом репозитория."
                ),
                "samples": manifest,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return manifest_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Сгенерировать синтетический OCR-набор.")
    parser.add_argument(
        "--out",
        type=Path,
        # Не `data/`: этот каталог целиком в .gitignore, а набор нужно коммитить.
        default=Path(__file__).resolve().parents[3] / "tests" / "ocr" / "fixtures" / "synthetic",
        help="Каталог для PNG и manifest.json",
    )
    parser.add_argument("--seed", type=int, default=20261029)
    args = parser.parse_args()
    path = write_dataset(args.out, seed=args.seed)
    print(f"written: {path}")
