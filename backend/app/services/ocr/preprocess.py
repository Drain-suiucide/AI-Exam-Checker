"""Предобработка изображения перед OCR.

Принципы:
- оригинал не изменяется: работаем с копией в памяти;
- каждый применённый шаг попадает в диагностику, чтобы результат был
  воспроизводим и объясним;
- предобработка консервативна: агрессивные фильтры могут стереть тонкие
  элементы букв и ухудшить распознавание;
- никакого «улучшения» текста: только геометрия и контраст.

Шаги применяются только при необходимости (по измеренным признакам), а не
всегда — иначе мы меняем входные данные там, где движок справился бы сам.
"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageFilter, ImageOps

#: Минимальная высота изображения: ниже растягиваем. Ориентируемся на высоту
#: страницы, а не строки, чтобы не гадать про размер шрифта.
#: Значение 300 выбрано на выборке `dev` (см. docs/evaluation/ocr_evaluation.md):
#: при 1000 абзац в 3–5 строк растягивался в 5 раз, штрихи «I» в римских цифрах
#: размывались (4/9 сохранено при 300 против 1/9 при 1000), а без растяжения
#: заметно хуже `low_res` (27 правок против 2). Для настоящих сканов порог не проверялся.
_MIN_OCR_HEIGHT = 300
_MAX_OCR_HEIGHT = 4000

#: Ниже этого среднего контраста считаем скан «плоским» и растягиваем уровни.
_LOW_CONTRAST_THRESHOLD = 45.0


@dataclass(frozen=True, slots=True)
class PreprocessedPage:
    """Результат предобработки: изображение + описание применённых шагов."""

    image: Image.Image
    steps: tuple[str, ...]
    rotation_applied_deg: float = 0.0
    warnings: tuple[str, ...] = ()


def _to_grayscale(image: Image.Image) -> Image.Image:
    """Привести к L. OCR не нужен цвет, а L втрое меньше по памяти."""
    if image.mode == "L":
        return image
    if image.mode in ("RGBA", "LA", "P"):
        # Прозрачность заливаем белым: иначе на чёрном фоне текст пропадёт.
        rgba = image.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        background.alpha_composite(rgba)
        return background.convert("L")
    return image.convert("L")


def _mean_contrast(image: Image.Image) -> float:
    """Грубая оценка контраста: размах между 5-м и 95-м перцентилем."""
    histogram = image.histogram()
    total = sum(histogram)
    if total == 0:
        return 0.0

    def percentile(share: float) -> int:
        target = total * share
        cumulative = 0
        for value, count in enumerate(histogram):
            cumulative += count
            if cumulative >= target:
                return value
        return 255

    return float(percentile(0.95) - percentile(0.05))


def _has_transparent_background(image: Image.Image) -> bool:
    if image.mode not in ("RGBA", "LA", "P"):
        return False
    alpha = image.convert("RGBA").getchannel("A")
    low, high = alpha.getextrema()
    return low < 250 and high > 0


def _resize_for_ocr(image: Image.Image) -> tuple[Image.Image, str | None]:
    """Масштабировать слишком мелкое/крупное изображение до рабочего диапазона."""
    width, height = image.size
    if height < _MIN_OCR_HEIGHT:
        scale = _MIN_OCR_HEIGHT / height
        new_size = (max(1, round(width * scale)), _MIN_OCR_HEIGHT)
        return image.resize(new_size, Image.Resampling.LANCZOS), f"upscale_x{scale:.2f}"
    if height > _MAX_OCR_HEIGHT:
        scale = _MAX_OCR_HEIGHT / height
        new_size = (max(1, round(width * scale)), _MAX_OCR_HEIGHT)
        return image.resize(new_size, Image.Resampling.LANCZOS), f"downscale_x{scale:.2f}"
    return image, None


def _projection_score(image: Image.Image) -> float:
    """Насколько «строками» расположен текст: сумма квадратов разностей профиля.

    `Image.getprojection()` — C-реализация суммы пикселей по строкам. Для
    одноканального изображения возвращается список чисел; для многоканального —
    список кортежей, поэтому приводим к `L` явно. Когда строки текста
    горизонтальны, профиль имеет резкие перепады между строкой и межстрочным
    пробелом, и метрика растёт.
    """
    gray = image if image.mode == "L" else image.convert("L")
    profile = gray.getprojection()
    # Pillow 13 возвращает список кортежей даже для режима `L`; берём канал.
    rows = [row[0] if isinstance(row, (tuple, list)) else row for row in profile]
    return float(sum((right - left) ** 2 for left, right in zip(rows, rows[1:], strict=False)))


def _deskew(image: Image.Image) -> tuple[Image.Image, float]:
    """Выровнять небольшой наклон по проекционному профилю.

    Перебираем малые углы и выбираем тот, при котором текст лучше всего
    «выстраивается» в строки.

    Большие углы не трогаем: поворот на 90/180 — это отдельная задача
    ориентации страницы, и «на глаз» её решать опасно.
    """
    small = image.copy()
    small.thumbnail((1200, 1200))

    best_angle = 0.0
    best_score = _projection_score(small)
    for angle in (-4, -3, -2, -1, 1, 2, 3, 4):
        rotated = small.rotate(
            angle, resample=Image.Resampling.BILINEAR, fillcolor=255, expand=False
        )
        score = _projection_score(rotated)
        if score > best_score:
            best_score = score
            best_angle = float(angle)

    if best_angle == 0.0:
        return image, 0.0
    rotated = image.rotate(
        best_angle, resample=Image.Resampling.BICUBIC, fillcolor=255, expand=True
    )
    return rotated, best_angle


def preprocess(image: Image.Image, *, deskew: bool = True) -> PreprocessedPage:
    """Подготовить страницу к распознаванию.

    Порядок шагов важен: прозрачность -> оттенки серого -> масштаб ->
    контраст -> выравнивание. Выравнивание идёт последним, потому что
    масштабирование меняет геометрию.
    """
    steps: list[str] = []
    warnings: list[str] = []
    working = image

    if _has_transparent_background(working):
        working = _to_grayscale(working)
        steps.append("flatten_alpha")
    elif working.mode != "L":
        working = _to_grayscale(working)
        steps.append("grayscale")

    working, resize_step = _resize_for_ocr(working)
    if resize_step:
        steps.append(resize_step)

    if _mean_contrast(working) < _LOW_CONTRAST_THRESHOLD:
        working = ImageOps.autocontrast(working, cutoff=1)
        steps.append("autocontrast")

    # Лёгкое подавление шума: медиана 3x3 убирает соль-перец от сканера,
    # не размывая штрихи так, как гауссово размытие.
    working = working.filter(ImageFilter.MedianFilter(size=3))
    steps.append("median_denoise")

    rotation = 0.0
    if deskew:
        working, rotation = _deskew(working)
        if rotation:
            steps.append(f"deskew_{rotation:+.0f}deg")
        else:
            steps.append("deskew_noop")

    return PreprocessedPage(
        image=working,
        steps=tuple(steps),
        rotation_applied_deg=rotation,
        warnings=tuple(warnings),
    )
