# Screen Specifications — AI Exam Checker

## 1. Общий сценарий

Сценарий демонстрации строится вокруг короткого и понятного пользовательского пути:

1. Главная страница с объяснением продукта;
2. Загрузка изображения / ввод ответа;
3. Выбор экзамена, года и задания;
4. Предпросмотр файла;
5. Исправление OCR;
6. Результат с оценкой по критериям;
7. Обоснование и фрагменты ответа;
8. Статус экспертной проверки;
9. Методика и ограничения прототипа;
10. Состояния ошибок и недоступности.

## 2. Экран 1 — Главная страница

### Цель
Показать ценность продукта, его ограничение как исследования и объяснить, что система помогает оценивать развернутый ответ по истории с объяснениями.

### Компоненты
- Header with product name and CTA;
- Hero section with headline, subheadline, supporting text;
- Primary CTA: «Проверить ответ»;
- Secondary CTA: «Узнать методику»;
- 3 KPI cards: «OCR», «Критерии», «Обоснование»;
- Illustrative SVG in the right column;
- Short workflow list: Upload → OCR → Verification → Explanation.

### Тексты
- Заголовок: «Проверка развёрнутого ответа по истории — быстро и объяснимо»;
- Подзаголовок: «AI Exam Checker помогает показать, как автоматически распознаётся ответ, проверяется по критериям и формируется предварительная оценка»;
- Дополнительный текст: «Прототип предназначен для исследования и демонстрации подхода; результат — предварительный, не заменяет экспертную проверку».

### Состояния
- Default / hover / focus / loading of CTA;
- Responsive hero layout for desktop and mobile.

### Действия пользователя
- Клик по CTA ведёт в сценарий загрузки;
- Клик по «Узнать методику» — к разделу про ограничения.

### Адаптивность
- На десктопе hero 2-column with illustration to right;
- На мобильном — illustration first or after heading, stacked.

### Доступность
- Contrast ratio at least 4.5:1 for text;
- Buttons with clear labels and focus ring;
- Use semantic heading hierarchy.

---

## 3. Экран 2 — Загрузка ответа / ввод текста

### Цель
Позволить пользователю загрузить скан или вставить текст вручную.

### Компоненты
- Section label: «Проверка ответа»;
- Card with upload zone:
  - drag and drop area;
  - supported types: image JPG/PNG;
  - hint: no personal information;
- Secondary input: textarea for manual text insertion;
- Selection summary chips: subject / exam / year / task.
- Primary button: «Далее».

### Состояния
- Empty upload zone;
- File selected;
- Error: unsupported file type;
- Error: server unavailable;
- File too large-sized.

### Тексты
- «Загрузите скан ответа или вставьте текст»;
- «Поддерживаются изображения JPG, PNG»;
- «Для тестов используйте синтетические или обезличенные примеры»;
- «В MVP допускается один предмет и один тип задания».

### Действия пользователя
- Upload file;
- Apply drag-and-drop;
- Paste text manually;
- Continue to the configuration screen.

### Адаптивность
- Upload zone expands vertically on smaller screens;
- Textarea remains usable without horizontal scrolling;
- Primary button wraps below secondary controls if layout tight.

### Доступность
- File input must have clear label or programmatic description;
- Error messages must be announced with `aria-live` region;
- Color not the only marker for invalid upload state.

---

## 4. Экран 3 — Выбор экзамена, года и задания

### Цель
Показать, что проверка доступна только по подтверждённым конфигурациям, и зафиксировать исследовательское ограничение MVP.

### Компоненты
- Header with step indicator: 1/5 or 1/6;
- Dropdowns or card selectors:
  - Предмет: История
  - Экзамен: ЕГЭ
  - Год: 2026
  - Задание: 19 (при подтверждённой конфигурации)
- Inline footnote: «Только подтверждённые конфигурации доступны в прототипе»;
- Secondary actions: «Назад» / «Продолжить».

### Состояния
- Valid selection;
- Disabled option for non-confirmed config;
- Empty state when no config available.

### Тексты
- «Подтверждённая конфигурация: История / ЕГЭ / 2026 / Задание 19»;
- «В исследовательском MVP используются только подтверждённые варианты проверки»;
- «Иные предметы и задания временно недоступны».

### Действия пользователя
- Choose exam config;
- Confirm selection;
- Continue only if config is valid.

### Адаптивность
- Dropdowns align in 2 columns on desktop and stack on mobile.
- Confirm banner remains visible above action buttons.

### Доступность
- Required fields must be clearly marked;
- Keyboard navigation between fields must be clear;
- Disabled selections must be distinguishable without relying on color alone.

---

## 5. Экран 4 — Предпросмотр загруженного изображения

### Цель
Проверить, что система отсканировала правильное изображение и пользователь успел заметить возможные ошибки до распознавания.

### Компоненты
- Large image preview area;
- Overlay metadata: filename, dimensions, uploaded time;
- Actions: «Заменить файл», «Исправить распознанный текст»;
- Minimal crop/zoom controls (optional, should remain subtle in MVP);
- Footer note: «Проверка не сохраняет реальные данные обучающихся».

### Состояния
- Loaded image;
- Error preview if file unreadable;
- Loading placeholder while file is processed.

### Тексты
- «Проверьте изображение перед OCR»;
- «Скан ответа будет распознан автоматически»;
- «Реальные данные не используются в демонстрационной среде».

### Действия пользователя
- Review image;
- Replace image if wrong;
- Proceed to OCR editing page.

### Адаптивность
- Image preview max-height 480px on desktop, full width in mobile;
- Control row wraps beneath image on small screens.

### Доступность
- Add `alt` description to any non-decorative image content;
- Make controls keyboard reachable;
- Ensure overlay text remains readable against image background.

---

## 6. Экран 5 — Исправление распознанного текста

### Цель
Дать пользователю возможность проверить OCR и исправить неточности до оценки.

### Компоненты
- Left panel: original image, with text blocks mapped if available;
- Right panel: editable OCR text area;
- Toolbar with quick actions: italic highlight, clear formatting, reset text, apply corrections;
- Confidence chips for uncertain segments (if implemented);
- Footer actions: «Назад», «Запустить проверку».

### Состояния
- OCR in progress;
- OCR ready for editing;
- Low-confidence markers visible;
- Error if model fails to generate text.

### Тексты
- «Проверьте распознанный текст и исправьте ошибки перед оценкой»;
- «Отдельные фрагменты отмечены как спорные»;
- «Исправления влияют только на этот сценарий проверки».

### Действия пользователя
- Edit text;
- Mark unclear fragments;
- Start evaluation.

### Адаптивность
- Two-column layout on desktop;
- Stacked layout on mobile with text panel first or second depending on screen size;
- Textarea should have min-height of 240px.

### Доступность
- Textarea labelled explicitly;
- Means to highlight low-confidence fragments without visual-only dependency;
- High contrast for highlighted warnings.

---

## 7. Экран 6 — Результат с баллами по каждому критерию

### Цель
Показать итоговую оценку и сделать результат прозрачным и проверяемым.

### Компоненты
- Top summary card: total score and status;
- Criteria section, each with: name, score, confidence, note;
- Optional progress bar for overall confidence;
- Action buttons: «Показать объяснение», «Скачать отчёт»;
- Secondary CTA: «Вернуться к тексту».

### Состояния
- Success result;
- Partial result;
- Expert review required;
- No result due to processing error.

### Тексты
- «Предварительная оценка»;
- «Критерий 1 — определение понятия»;
- «Критерий 2 — исторический факт / конкретизация»;
- «Низкая уверенность по одному из критериев»;
- «Результат может потребовать экспертной проверки».

### Действия пользователя
- View overall score;
- Inspect each criterion;
- Navigate to evidence panel.

### Адаптивность
- Summary metrics placed in a row on desktop and stack on mobile;
- Criteria table wraps cleanly on smaller screens.

### Доступность
- Score values clearly associated with criteria names;
- Summaries should be readable without relying on color alone;
- Ensure each action has accessible label.

---

## 8. Экран 7 — Панель обоснования

### Цель
Показать, какие фрагменты ответа подтвердили оценку и почему.

### Компоненты
- Three-column block or side-by-side layout:
  1. response fragment;
  2. criterion;
  3. explanation;
- Segment highlight markers with confidence tag;
- Expandable details for disputed parts;
- Short footnote: «Обоснование — это не окончательная экспертная оценка».

### Состояния
- Good evidence;
- Ambiguous evidence;
- Evidence not found;
- Criterion with low-confidence interpretation.

### Тексты
- «Фрагмент ответа»;
- «Применённый критерий»;
- «Почему это оценено так»;
- «Не все фрагменты удалось однозначно интерпретировать».

### Действия пользователя
- Expand explanation;
- Jump to relevant answer fragment;
- Return to criterion summary.

### Адаптивность
- On mobile the evidence card becomes stacked with heading above content.

### Доступность
- Evidence list should remain keyboard navigable;
- Use descriptive heading structure instead of relying solely on color coding.

---

## 9. Экран 8 — Требуется экспертная проверка

### Цель
Демонстрировать режим, когда результат не может считаться уверенным и требуется участие эксперта.

### Компоненты
- Warning card with icon;
- Clear explanatory text;
- “What this means” bullet list;
- Secondary CTA: «Вернуться к результату»;
- Optional tertiary CTA: «Подробнее о методике».

### Состояния
- Warning visible;
- Warning resolved after expert review;
- Warning plus issue description.

### Тексты
- «Требуется экспертная проверка»;
- «Автоматическая система не уверена в корректности интерпретации текста или критерия»;
- «Этот статус не означает, что ответ неверный; он означает, что необходимо проверить логику и формулу оценки».

### Действия пользователя
- View issue summary;
- Open methodology section;
- Resume review.

### Доступность
- Use icon + label + text; do not rely on icons alone;
- Warning text must be concise but complete.

---

## 10. Экран 9 — Методика и ограничения прототипа

### Цель
Сделать прозрачным, что система является исследовательским прототипом с заранее известными ограничениями.

### Компоненты
- Intro card with method description;
- 3–4 blocks: what is checked, what is not checked, how confidence is assessed, what needs expert review;
- Footer note on data safety and synthetic examples.

### Тексты
- «Исследовательский MVP»;
- «Проверяется развернутый ответ по истории; нужно и фактическое знание, и точность формулировки»;
- «В прототипе не используются реальные данные учащихся»;
- «Автоматическая оценка не заменяет экспертное решение».

### Действия пользователя
- Read methodology;
- Return to result or main flow;
- Explore constraints.

### Адаптивность
- Section cards convert to single-column on smaller widths.

### Доступность
- Headings and lists must be accessible;
- Ensure method blocks remain readable even in reduced motion mode.

---

## 11. Состояния ошибок и недоступности

### Ошибка загрузки
- File type unsupported;
- File not parsed;
- Network unavailable;
- OCR timeout.

### UX-решение
- Show inline alert card with action buttons;
- Provide one primary retry action and one secondary fallback.

### Текст шаблона
- «Не удалось обработать изображение. Проверьте файл и попробуйте ещё раз»;
- «Сервер временно недоступен. Повторите попытку позже»;
- «Результат не сформирован. Проверьте конфигурацию и параметры запроса».

### Доступность
- Inline alerts must be perceivable and focusable.

---

## 12. Набор текстов в стиле продукта

Рекомендуемые формулировки для основных действий:

- «Проверить ответ»;
- «Загрузить файл»;
- «Указать вручную»;
- «Проверить распознанный текст»;
- «Запустить проверку»;
- «Показать объяснение»;
- «Вернуться к результату»;
- «Подробнее о методике»;
- «Скачать отчёт»;
- «Заменить файл».

## 13. Критерии готовности экрана

Экран считается готовым, если:
- он имеет понятное значение и цель;
- он решает конкретный шаг пользовательского сценария;
- у него есть чёткие состояния успеха/ошибки/ожидания;
- он поддерживает доступность и адаптивность;
- он не вводит пользователя в заблуждение относительно статуса оценки.
