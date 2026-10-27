# Accessibility Checklist — AI Exam Checker

## 1. Принципы

Интерфейс должен быть доступен для пользователей с разными возможностями и работать без визуального контекста. Основной приоритет — понятность и предсказуемость интерфейса, а не только «формальное» следование стандартам.

Цели:
- обеспечить читаемость и навигацию без мыши;
- сохранить понятность при изменении масштаба и цветов;
- сделать статусы и ошибки понятными для всех пользователей;
- предотвратить зависимость от одного только цвета и визуальной эстетики.

## 2. Основные требования

### 2.1. Семантика
- Use semantic headings (`h1`, `h2`, `h3`) in logical order.
- All interactive elements must have programmatically associated labels.
- Use lists and groups for repeated items, such as criteria, evidence and steps.
- Every page should expose a clear page title.

### 2.2. Навигация
- Ensure full keyboard accessibility for buttons, inputs, dropdowns, tabs, and links.
- Maintain visible focus indicator with contrast at least 3:1 against adjacent colors.
- Do not trap focus in modals or file upload flows.
- Use skip links for long forms if necessary.

### 2.3. Цвет и контраст
- Minimum text contrast ratio: 4.5:1 for body text; 3:1 for large text and UI components.
- Do not encode important state only with color (for example: score 0/1/2 + text label + icon).
- Provide sufficient contrast for status badges and error messages.

### 2.4. Формы и ввод
- Required fields must be clearly labelled.
- File upload controls must have visible labels and descriptions.
- Error messages must be associated with the fields and announced to screen readers.
- Do not rely on drag-and-drop only for core functionality; also provide manual file selection.

### 2.5. Содержимое и речь
- Text should be brief, direct, and free from unexplained acronyms.
- First use of acronym should be clarified: «OCR (распознавание текста)».
- Avoid jargon unless it is connected to a helper text or explanation.

## 3. Проверка по экранам

### 3.1. Главная страница
- Hero CTA must be keyboard accessible and labeled.
- Illustrations must be decorative or include text alternatives if informative.
- User should understand what the product does without reading long paragraphs.

### 3.2. Загрузка ответа
- Upload area must not rely solely on visual drag behavior.
- Manual paste and file selection should both be available.
- Error states must include a text explanation, not only a red border.

### 3.3. Выбор экзамена и задания
- Options should be clear and grouped.
- Disabled selections should be visually distinct and programmatically readable.
- The current validated configuration should be shown as a clear summary.

### 3.4. Предпросмотр изображения
- Image preview should not destroy content because of poor contrast.
- If an image is displayed, some metadata should be readable by assistive tech as text.
- Controls to replace image should have clear labels.

### 3.5. Исправление OCR
- Textarea must have explicit label and visible instructions.
- Low-confidence markers must be perceivable in text too, not just by color.
- Text can be edited without causing blurred or hidden content.

### 3.6. Результат и критерии
- Each criterion should be in a semantic list or table.
- Score and status should be communicated in text as well as visual color.
- “Expert review required” state should be clearly labelled and explained.

### 3.7. Обоснование
- Evidence should be accessible as structured blocks or list items.
- Make it easy to jump between evidence and the corresponding part of the answer.
- Provide a clear distinction between “evaluated as correct” and “evaluated as uncertain”.

### 3.8. Методика и ограничения
- Provide straightforward plain-language summaries.
- Link to details without requiring users to infer by context.
- Keep the section scannable with short paragraphs and subheadings.

## 4. Проверка для пользователей с особыми потребностями

### 4.1. Для пользователей с нарушениями зрения
- Ensure minimum 16px font or equivalent scaling.
- Support browser zoom up to 200% without content breakage.
- Do not use text embedded in images as the only carrier of meaning.
- Ensure icons and status markers have textual equivalents.

### 4.2. Для пользователей с ограничениями моторики
- Buttons should have at least 44x44 px touch target.
- Every action should be available via keyboard.
- Avoid hover-only interactions or hidden controls.

### 4.3. Для пользователей с когнитивными ограничениями
- Keep one task per screen and avoid ambiguous labels.
- Use plain language for content and actions.
- Separate “what happened” and “what to do next” in alerts.

### 4.4. Для пользователей с нарушениями слуха
- All critical information is visual and textual; no reliance on audio cues.
- Status and system messages are communicated in text.

## 5. Состояния и элементы, которые требуют особого внимания

- loading state;
- error state;
- file upload state;
- OCR confidence markers;
- expert review warning;
- no result available state;
- network/server unavailable state.

Each of these states must be explained in plain language and not rely on color alone.

## 6. Рекомендуемые проверки перед сдачей

- Keyboard-only pass across all critical flows.
- Zoom to 200% and check layout integrity.
- Switch to high contrast mode or inspect palette and contrast ratios.
- Screen reader pass for main scenario: upload → OCR edit → evaluation → explanation.
- Validate focus order and labels for buttons and forms.
- Check error messages for clear language and next steps.

## 7. Критерий выхода

Дизайн считается доступным, если:
- все ключевые действия доступны с помощью клавиатуры;
- визуальная информация дублируется текстом;
- цвет не является единственным способом различения состояний;
- пользователь может выполнить сценарий без мыши и без сложной визуальной интерпретации;
- критические ошибки, предупреждения и ограничения описаны простым языком.
