# API_CONTRACT

Статус: **Proposed** (T-003). Источник истины для имён полей, форматов ответов и кодов ошибок.
Изменение контракта требует согласования с владельцем проекта (см. PROJECT_CONTEXT.md) и записи в CHANGELOG.md.

Связанные документы: [ARCHITECTURE.md](ARCHITECTURE.md), [DATA_MODEL.md](DATA_MODEL.md), [DECISIONS/ADR-003-evaluation-versioning.md](DECISIONS/ADR-003-evaluation-versioning.md).

---

## 1. Общие соглашения

| Параметр | Значение |
|---|---|
| Базовый путь | `/api/v1` (кроме `GET /health`) |
| Формат | JSON, UTF-8, ключи `snake_case`; исключение: `POST /submissions` принимает `multipart/form-data` |
| Идентификаторы | UUID v4, строчные, через дефис |
| Время | ISO 8601 UTC с суффиксом `Z`: `2026-10-26T12:00:00Z` |
| Оценки | целые числа |
| Уверенность (`confidence`) | число `0.00–1.00`, 2 знака. Это **самооценка модели, не калиброванная вероятность** |
| Перечисления | строки в нижнем регистре `snake_case`; исключение: флаги (`LOW_CONFIDENCE`) и коды ошибок (`INVALID_STATE`) — в верхнем |
| Смещения текста | `char_start` включительно, `char_end` не включительно; считаются в **кодовых точках Unicode** по NFC-нормализованному `text` (в Python — индексы `str`; в JS для кириллицы совпадают с индексами строки) |
| Заголовок запроса | `X-Request-ID` (необязателен; если нет, сервер генерирует). Эхо в каждом ответе |
| Кэширование | все ответы с данными пользователя: `Cache-Control: no-store` |

### 1.1 Доступ

Аккаунтов нет. Используются два вида доступа:

| Метка | Как передаётся | Что даёт |
|---|---|---|
| `public` | ничего | `GET /health`, `GET /exam-configurations`, `POST /submissions` |
| `submitter` | заголовок `X-Submission-Token: sbt_...` | операции над **своей** отправкой |
| `expert` | заголовок `X-Expert-Key: <key>` | чтение любых отправок, очередь проверок, вынесение решения |

- Токен отправки выдаётся один раз в ответе `201` на `POST /submissions` (поле `access_token`). Токен детерминированно выводится из `id` отправки и серверного секрета `SUBMISSION_TOKEN_SECRET` (HMAC-SHA256), поэтому в БД не хранится и воспроизводится при повторном идемпотентном запросе.
- Ключи экспертов задаются переменной окружения `EXPERT_KEYS` (`label:key,label:key`). `label` — псевдоним, попадает в `decided_by` и аудит.
- Эксперт с `X-Expert-Key` может вызывать **только чтение** маршрутов `submitter` (отправка, файлы, транскрипция, результат). Изменяющие маршруты отправки (`recognize`, `PATCH transcription`, `evaluate`, `DELETE`, создание запроса проверки) для эксперта запрещены (`FORBIDDEN`).
- Неверный токен для существующего `id` отвечает `404 NOT_FOUND` (существование отправки не раскрывается). Отсутствие заголовка — `401 UNAUTHORIZED`.
- Браузерный `<img src>` не может передать заголовок: файлы получаем через `fetch` и `URL.createObjectURL`.

### 1.2 Формат ошибки

Все ошибки (4xx, 5xx) имеют единый вид:

```json
{
  "error": {
    "code": "INVALID_STATE",
    "message": "Действие недоступно в текущем состоянии отправки.",
    "details": { "current_status": "recognizing", "allowed_actions": ["delete"] },
    "request_id": "c3f1c0de-0000-4000-8000-000000000000"
  }
}
```

`code` стабилен и используется клиентом; `message` — человекочитаемый текст на русском, может меняться. `details` — объект или `null`.
Для `VALIDATION_ERROR`: `details = { "fields": [ { "loc": ["body","text"], "code": "too_short", "message": "..." } ] }`.

### 1.3 Каталог кодов ошибок

| HTTP | `code` | Когда |
|---|---|---|
| 400 | `BAD_REQUEST` | Невалидный JSON/multipart, неверный формат заголовка |
| 401 | `UNAUTHORIZED` | Нет `X-Submission-Token` / `X-Expert-Key` там, где нужен |
| 403 | `FORBIDDEN` | Креденшл валиден, но действие запрещено (эксперт пытается изменить отправку; токен отправки на экспертном маршруте; запрос неутверждённых конфигураций в production) |
| 404 | `NOT_FOUND` | Ресурса нет или токен не подходит |
| 404 | `EXAM_CONFIGURATION_NOT_FOUND` | Неизвестный `exam_configuration_id` |
| 409 | `CONFIGURATION_NOT_APPROVED` | Конфигурация не `approved`, а `ALLOW_UNAPPROVED_CONFIG=false` |
| 409 | `INVALID_STATE` | Действие недопустимо в текущем `status` (в `details`: `current_status`, `allowed_actions`) |
| 409 | `TRANSCRIPTION_VERSION_CONFLICT` | `base_version` / `transcription_version` не совпадает с текущей версией (в `details.current_version`) |
| 409 | `RESULT_NOT_READY` | Нет успешной оценки (в `details.submission_status`) |
| 409 | `DECISION_ALREADY_EXISTS` | Для запроса проверки уже есть решение с другим содержимым |
| 413 | `PAYLOAD_TOO_LARGE` | Превышен размер тела или файла |
| 415 | `UNSUPPORTED_MEDIA_TYPE` | Тип файла не из `limits.allowed_mime_types` (определяется по содержимому, не по заголовку клиента) |
| 422 | `VALIDATION_ERROR` | Нарушены правила валидации полей |
| 422 | `INVALID_IMAGE` | Файл не декодируется, слишком много пикселей, повреждён |
| 429 | `RATE_LIMITED` | Превышен лимит попыток (например, 3 неудачных оценки на одну транскрипцию) |
| 429 | `DAILY_QUOTA_EXCEEDED` | Исчерпан `MAX_EVALUATIONS_PER_DAY` |
| 500 | `INTERNAL_ERROR` | Непредвиденная ошибка (детали только в логах) |
| 503 | `SERVICE_UNAVAILABLE` | БД недоступна |

Ошибки **фоновой обработки** не возвращаются как HTTP-ошибки, а лежат в `recognition.error` / `evaluation.error` объекта `Submission` (код + сообщение):

| Источник | Коды |
|---|---|
| Распознавание | `OCR_TIMEOUT`, `OCR_ENGINE_ERROR`, `OCR_EMPTY_RESULT`, `INTERRUPTED` |
| Оценивание | `LLM_TIMEOUT`, `LLM_PROVIDER_ERROR`, `LLM_INVALID_OUTPUT`, `EVALUATION_INTERNAL_ERROR`, `INTERRUPTED` |

`INTERRUPTED` — процесс перезапущен или прошёл тайм-аут, пока шла обработка (см. ARCHITECTURE.md, п. 8).

### 1.4 Идемпотентность

| Маршрут | Механизм |
|---|---|
| `POST /submissions` | Заголовок `Idempotency-Key` (строка 8–64 символа `[A-Za-z0-9_-]`). Повтор с тем же ключом и тем же телом → `200` с той же отправкой и заголовком `Idempotent-Replay: true`. Тот же ключ, другое тело → `422 VALIDATION_ERROR` (`code: idempotency_key_reused`). Ключ необязателен для curl, **обязателен для frontend** |
| `POST .../recognize`, `POST .../evaluate` | По состоянию: повторный вызов во время выполнения возвращает текущее состояние (`200`), а не запускает второй процесс |
| `POST .../review-requests` | На одну оценку — не более одного запроса; повтор возвращает существующий (`200`, `Idempotent-Replay: true`), тело повтора игнорируется |
| `POST .../decision` | Одно решение на запрос; повтор с тем же содержимым → `200`; с другим → `409 DECISION_ALREADY_EXISTS` |
| `PATCH .../transcription` | Тот же `text`, что в текущей версии → `200` без новой версии |
| `DELETE` | Повтор вернёт `404` — клиент считает это успехом |

### 1.5 Пагинация

Только `GET /review-requests`: `limit` (1–50, по умолчанию 20), `cursor` (непрозрачная строка). Ответ: `{ "items": [...], "next_cursor": string | null }`.

### 1.6 Сводные лимиты и сроки

Значения по умолчанию; для конкретной конфигурации лимиты файлов и текста лежат в `ExamConfiguration.limits`, но не могут превышать жёсткие пределы сервера.

| Параметр | Значение |
|---|---|
| Файлов в отправке | 1–4 (страницы по порядку) |
| Размер одного файла | ≤ 8 MiB |
| Тело `POST /submissions` | ≤ 36 MiB (проверяется потоково до чтения целиком → `413`) |
| Разрешённые типы | `image/jpeg`, `image/png`, `image/webp` (PDF и HEIC не поддерживаются в MVP) |
| Размер изображения | ≤ 40 Мпикс; после нормализации длинная сторона ≤ 4096 px |
| Длина ответа (текст) | 10–10 000 символов после обрезки пробелов |
| Комментарий к запросу проверки | ≤ 1000 символов; комментарий эксперта ≤ 2000 |
| Обычные запросы (GET/PATCH/DELETE) | ответ ≤ 5 с |
| `POST /submissions` | ≤ 30 с |
| Распознавание (фон) | ≤ 60 с (`OCR_TIMEOUT_S`) |
| Оценивание (фон) | ≤ 90 с (`EVAL_TIMEOUT_S`) |
| Опрос статуса | клиент опрашивает `GET /submissions/{id}` каждые `poll_interval_ms` (2000 мс) |
| Неудачных оценок на одну транскрипцию | ≤ 3 |
| Оценок в сутки (глобально) | `MAX_EVALUATIONS_PER_DAY`, по умолчанию 200 |

---

## 2. Общие схемы

Нотация TypeScript используется только для описания форм. `T | null` означает, что поле **всегда присутствует** и может быть `null`; необязательных (отсутствующих) полей в ответах нет.

```ts
type UUID = string;
type Timestamp = string;      // ISO 8601 UTC
type Confidence = number;     // 0.00–1.00
type Sha256 = string;         // 64 hex-символа, строчные

type SubmissionStatus =
  | "ready_for_recognition"   // изображение загружено, текста ещё нет
  | "recognizing"
  | "recognition_failed"      // OCR не удался, текста нет
  | "ready_for_evaluation"    // есть текущая транскрипция, оценки для неё нет
  | "evaluating"
  | "evaluation_failed"
  | "evaluated";              // для текущей транскрипции есть успешная оценка

type Action =
  | "recognize" | "edit_transcription" | "evaluate"
  | "view_result" | "request_review" | "delete";

type Flag = "LOW_CONFIDENCE" | "NO_EVIDENCE_FOUND" | "AMBIGUOUS" | "OCR_LOW_QUALITY";

interface ApiError { code: string; message: string }   // ошибка фоновой обработки
```

### 2.1 ExamConfiguration

Закреплённый набор версий: экзамен + задание + критерии + профиль оценивания. Неизменяем после утверждения (см. ADR-003).

```ts
interface ExamConfiguration {
  id: UUID;
  slug: string;                                  // например "ege-history-demo"
  status: "draft" | "approved" | "retired";
  is_default: boolean;
  exam: {
    code: string;                                // "ege-history"
    subject: string;                             // "history"
    title: string;
    version_label: string;
    exam_year: number;
  };
  task: {
    task_version_id: UUID;
    task_key: string;                            // стабильный идентификатор задания
    task_number: string | null;                  // null, пока номер не утверждён по ФИПИ
    version: number;
    title: string;
    statement: string;                           // текст задания
    materials: { kind: "text" | "list"; title: string; content: string }[];
    max_score: number;
  };
  criteria_version: {
    id: UUID;
    version: number;
    aggregation: { type: "sum" };                // только "sum" в MVP
    max_score_total: number;
    criteria: {
      id: UUID;
      code: string;                            // "K1", "K2", ...
      position: number;                        // порядок показа, с 1
      title: string;
      description: string;
      max_score: number;
      levels: { score: number; description: string }[];
    }[];
  };
  evaluation_profile: { id: UUID; code: string; version: number; model_provider: string; model_name: string };
  sources: { publisher: string; title: string; edition_label: string; url: string | null; retrieved_at: Timestamp | null }[];
  limits: {
    max_files: number;
    max_file_bytes: number;
    allowed_mime_types: string[];
    min_answer_chars: number;
    max_answer_chars: number;
  };
  created_at: Timestamp;
  approved_at: Timestamp | null;
}
```

### 2.2 Submission

```ts
interface Submission {
  id: UUID;
  status: SubmissionStatus;
  input_mode: "image" | "text";
  data_origin: "synthetic" | "anonymized";
  exam_configuration_id: UUID;
  exam_configuration_status: "draft" | "approved" | "retired";
  created_at: Timestamp;
  updated_at: Timestamp;
  expires_at: Timestamp | null;                  // после этого момента отправка удаляется
  files: FileInfo[];                             // пусто при input_mode = "text"
  current_transcription: TranscriptionSummary | null;
  recognition: RecognitionRun | null;            // последний запуск
  evaluation: EvaluationSummary | null;          // последняя попытка
  review_request: ReviewRequestSummary | null;
  allowed_actions: Action[];                     // вычисляется сервером; клиент не дублирует логику
  poll_interval_ms: number | null;               // 2000 при recognizing/evaluating, иначе null
}

interface SubmissionCreated extends Submission { access_token: string }  // только в ответе 201/200 на POST /submissions

interface FileInfo {
  id: UUID; page_index: number;                  // с 0
  mime_type: string; size_bytes: number; width_px: number; height_px: number; sha256: Sha256;
}

interface RecognitionRun {
  id: UUID; attempt_no: number;
  status: "running" | "succeeded" | "failed";
  engine: string; engine_version: string;
  started_at: Timestamp; finished_at: Timestamp | null;
  error: ApiError | null;
  transcription_id: UUID | null;                 // заполнено при succeeded
}

interface EvaluationSummary {
  id: UUID; attempt_no: number;
  status: "running" | "succeeded" | "failed";
  transcription_version: number;
  is_current: boolean;                           // оценка относится к текущей версии транскрипции
  started_at: Timestamp; finished_at: Timestamp | null;
  error: ApiError | null;
  total_score: number | null; max_score: number | null;
}

interface ReviewRequestSummary { id: UUID; status: "open" | "resolved"; created_at: Timestamp }
```

`allowed_actions` по состояниям:

| `status` | `allowed_actions` |
|---|---|
| `ready_for_recognition` | `recognize`, `edit_transcription`, `delete` |
| `recognizing` | — (пусто) |
| `recognition_failed` | `recognize`, `edit_transcription`, `delete` |
| `ready_for_evaluation` | `edit_transcription`, `evaluate`, `delete`, а при `input_mode = "image"` ещё `recognize` |
| `evaluating` | — (пусто) |
| `evaluation_failed` | `edit_transcription`, `evaluate`, `delete` |
| `evaluated` | `edit_transcription`, `view_result`, `request_review`, `delete` |

Если есть хоть одна успешная оценка (даже устаревшая), добавляется `view_result`; `request_review` добавляется, пока у последней успешной оценки нет запроса проверки.
Действия `edit_transcription`/`recognize`/`evaluate`/`delete` недоступны экспертному ключу независимо от списка.

### 2.3 Transcription

```ts
interface TranscriptionSummary {
  id: UUID; version: number;                     // с 1, растёт при каждой правке
  source: "ocr" | "manual_input" | "user_edit";
  char_count: number; text_sha256: Sha256; created_at: Timestamp;
}

interface Transcription extends TranscriptionSummary {
  text: string;                                  // NFC, переводы строк "\n"
  parent_version: number | null;
  ocr: {                                         // только для source = "ocr", иначе null
    mean_confidence: Confidence | null;
    segments: {
      index: number; page_index: number;
      char_start: number; char_end: number;      // смещения в text этой версии
      confidence: Confidence | null;
      bbox: [number, number, number, number] | null;   // нормализованные x0,y0,x1,y1 (0..1) на странице
    }[];
  } | null;
}
```

### 2.4 Evaluation (результат)

```ts
interface Evaluation {
  id: UUID;
  submission_id: UUID;
  status: "succeeded";                           // /result отдаёт только успешные
  transcription_id: UUID;
  transcription_version: number;
  is_current: boolean;                           // false, если текст правили после оценки
  versions: VersionStamp;
  total_score: number;
  max_score: number;
  overall_confidence: Confidence;                // минимум по критериям
  needs_review: boolean;                         // система советует экспертную проверку
  flags: Flag[];                                 // флаги уровня оценки
  summary: string | null;
  criteria: CriterionResult[];                   // в порядке position
  final: { total_score: number; max_score: number; source: "model" | "expert" };
  expert_review: ReviewRequest | null;           // с вложенным decision, если решение есть
  disclaimer: string;                            // "Ориентировочная оценка модели. Не является официальным баллом ЕГЭ."
  created_at: Timestamp;
}

interface VersionStamp {
  exam_configuration_id: UUID;
  exam_configuration_status: "draft" | "approved" | "retired";
  exam: { code: string; version_label: string; exam_year: number };
  task_version: { id: UUID; task_key: string; task_number: string | null; version: number; content_sha256: Sha256 };
  criteria_version: { id: UUID; version: number; content_sha256: Sha256 };
  evaluation_profile: { id: UUID; code: string; version: number; prompt_sha256: Sha256 };
  model: { provider: string; requested: string; reported: string | null };
  source_editions: { publisher: string; title: string; edition_label: string; url: string | null }[];
}

interface CriterionResult {
  criterion_id: UUID; code: string; title: string; position: number;
  score: number; max_score: number;
  confidence: Confidence;
  rationale: string;                             // обоснование по критерию
  uncertainty_note: string | null;               // «спорное место», если есть
  flags: Flag[];                                 // уровня критерия
  evidence: EvidenceRef[];
}

interface EvidenceRef {
  id: UUID;
  kind: "supports" | "deficiency";               // подтверждает балл / показывает ошибку или пробел
  char_start: number; char_end: number;          // смещения в transcription этой оценки
  quote: string;                                 // text[char_start:char_end], проверено сервером
  note: string | null;
}
```

Правила, которые гарантирует сервер: `0 ≤ score ≤ max_score`; `total_score` считает код, а не модель; каждый `evidence.quote` дословно равен подстроке транскрипции; недостоверные цитаты отбрасываются, а критерий с `score > 0` без достоверных `supports` получает флаг `NO_EVIDENCE_FOUND`.

### 2.5 ReviewRequest и ExpertDecision

```ts
interface ReviewRequest {
  id: UUID;
  submission_id: UUID;
  evaluation_id: UUID;
  status: "open" | "resolved";
  reason_code: "disagree_with_score" | "ocr_error" | "unclear_rationale" | "other";
  criterion_codes: string[];                     // спорные критерии; пусто = вся оценка
  comment: string | null;
  created_at: Timestamp;
  resolved_at: Timestamp | null;
  decision: ExpertDecision | null;
}

interface ExpertDecision {
  id: UUID;
  review_request_id: UUID;
  outcome: "confirmed" | "adjusted";
  criterion_adjustments: { criterion_code: string; original_score: number; score: number; comment: string | null }[];
  final_total_score: number;
  max_score: number;
  comment: string;
  decided_by: string;                            // label эксперта
  decided_at: Timestamp;
}
```

---

## 3. Маршруты

Сводка:

| # | Метод и путь | Доступ | Успех |
|---|---|---|---|
| 1 | `GET /health` | public | 200 |
| 2 | `GET /api/v1/exam-configurations` | public | 200 |
| 3 | `POST /api/v1/submissions` | public | 201 / 200 (повтор) |
| 4 | `GET /api/v1/submissions/{id}` | submitter, expert | 200 |
| 5 | `DELETE /api/v1/submissions/{id}` | submitter | 204 |
| 6 | `GET /api/v1/submissions/{id}/files/{file_id}/content` | submitter, expert | 200 (бинарный) |
| 7 | `POST /api/v1/submissions/{id}/recognize` | submitter | 202 / 200 |
| 8 | `GET /api/v1/submissions/{id}/transcription` | submitter, expert | 200 |
| 9 | `PATCH /api/v1/submissions/{id}/transcription` | submitter | 200 |
| 10 | `POST /api/v1/submissions/{id}/evaluate` | submitter | 202 / 200 |
| 11 | `GET /api/v1/submissions/{id}/result` | submitter, expert | 200 |
| 12 | `POST /api/v1/submissions/{id}/review-requests` | submitter | 201 / 200 (повтор) |
| 13 | `GET /api/v1/review-requests` | expert | 200 |
| 14 | `GET /api/v1/review-requests/{id}` | expert, submitter (своей отправки) | 200 |
| 15 | `POST /api/v1/review-requests/{id}/decision` | expert | 201 / 200 (повтор) |

Отличия от предварительного списка из задачи: добавлены `DELETE submission` (право пользователя удалить свои данные), `GET files/{file_id}/content` (показать скан рядом с распознанным текстом), `GET transcription` (получить текст для правки), `GET review-requests` (эксперту нужна очередь). Остальные маршруты сохранены.

---

### 3.1 `GET /health`

| | |
|---|---|
| Назначение | Проверка живости и доступности БД для Docker healthcheck |
| Доступ | public |
| Запрос | — |
| Ответ 200 | `{ "status": "ok", "version": "0.1.0", "git_sha": "abc1234" \| null, "checks": { "database": "ok" } }` |
| Ошибки | `503 SERVICE_UNAVAILABLE` с телом `{ "status": "degraded", "checks": { "database": "error" } }` (формат отличается от `ApiError` намеренно) |
| Валидация | — |
| Идемпотентность | безопасный |
| Лимиты | ответ ≤ 2 с; не логируется на уровне INFO |

### 3.2 `GET /api/v1/exam-configurations`

| | |
|---|---|
| Назначение | Список конфигураций, по которым можно проверять ответы |
| Доступ | public |
| Запрос | query `status`: `approved` (по умолчанию) \| `draft` \| `all`. Значения `draft`/`all` работают только при `ALLOW_UNAPPROVED_CONFIG=true`, иначе `403 FORBIDDEN` |
| Ответ 200 | `{ "items": ExamConfiguration[] }`; сортировка: `is_default` первым, затем `created_at` по убыванию |
| Ошибки | `403 FORBIDDEN` |
| Валидация | `status` из перечисления, иначе `422 VALIDATION_ERROR` |
| Идемпотентность | безопасный |
| Лимиты | ≤ 5 с; в MVP 1–3 элемента, пагинации нет |

Список содержит полные объекты, включая текст задания и критерии: отдельного маршрута деталей нет.

### 3.3 `POST /api/v1/submissions`

| | |
|---|---|
| Назначение | Создать отправку: загрузить скан или ввести текст вручную |
| Доступ | public |
| Content-Type | `multipart/form-data` (и для текста, и для изображений) |

Поля формы:

| Поле | Тип | Обязательно | Правила |
|---|---|---|---|
| `exam_configuration_id` | UUID | да | существует; `approved` либо разрешён `ALLOW_UNAPPROVED_CONFIG` |
| `data_origin` | `synthetic` \| `anonymized` | да | подтверждение, что в ответе нет реальных ПДн |
| `input_mode` | `image` \| `text` | да | |
| `text` | строка | если `input_mode = text` | длина по `limits`; нормализуется: NFC, `\r\n`→`\n`, удаляются управляющие символы кроме `\n`, `\t`, обрезаются пробелы по краям |
| `files` | файл (повторяемое поле) | если `input_mode = image` | `1..limits.max_files`; порядок полей = порядок страниц; запрещено совмещать с `text` |

Заголовки: `Idempotency-Key` (см. 1.4).

Ответ `201` (или `200` при идемпотентном повторе): `SubmissionCreated`, заголовок `Location: /api/v1/submissions/{id}`.
Начальный `status`: `ready_for_recognition` для `image`; `ready_for_evaluation` для `text` (сразу создаётся транскрипция версии 1 с `source = "manual_input"`).

Ошибки: `404 EXAM_CONFIGURATION_NOT_FOUND`, `409 CONFIGURATION_NOT_APPROVED`, `413 PAYLOAD_TOO_LARGE`, `415 UNSUPPORTED_MEDIA_TYPE`, `422 VALIDATION_ERROR`, `422 INVALID_IMAGE`, `429 RATE_LIMITED`, `400 BAD_REQUEST`.

Порядок проверок (от дешёвых к дорогим): размер тела → поля формы → конфигурация → для каждого файла: тип по сигнатуре, декодирование, число пикселей → нормализация (снятие EXIF, поворот по ориентации, ограничение размера) → запись в хранилище → транзакция БД. При ошибке на любом шаге записанные файлы удаляются.
Идемпотентность: `Idempotency-Key`. Лимиты: тело ≤ 36 MiB, время ≤ 30 с.

### 3.4 `GET /api/v1/submissions/{id}`

| | |
|---|---|
| Назначение | Текущее состояние отправки; основной маршрут опроса |
| Доступ | submitter, expert |
| Ответ 200 | `Submission` |
| Ошибки | `401 UNAUTHORIZED`, `404 NOT_FOUND` |
| Валидация | `id` — UUID, иначе `404 NOT_FOUND` |
| Идемпотентность | безопасный |
| Лимиты | ≤ 5 с |

Побочный эффект: если фоновый процесс висит дольше тайм-аута + 30 с, GET помечает запуск как `failed` с кодом `INTERRUPTED` и возвращает отправку в соответствующее состояние (см. ARCHITECTURE.md, п. 8).

### 3.5 `DELETE /api/v1/submissions/{id}`

| | |
|---|---|
| Назначение | Немедленно удалить отправку со всеми файлами, текстами, оценками и запросами проверки |
| Доступ | submitter |
| Ответ | `204` без тела |
| Ошибки | `401`, `403` (эксперт), `404`, `409 INVALID_STATE` (идёт `recognizing`/`evaluating`) |
| Идемпотентность | повтор вернёт `404` |
| Лимиты | ≤ 5 с |

Журнал аудита сохраняется (без содержимого).

### 3.6 `GET /api/v1/submissions/{id}/files/{file_id}/content`

| | |
|---|---|
| Назначение | Получить нормализованное изображение страницы |
| Доступ | submitter, expert |
| Ответ 200 | бинарное тело; `Content-Type` = `FileInfo.mime_type`; `Content-Disposition: inline`; `X-Content-Type-Options: nosniff`; `Cache-Control: private, no-store` |
| Ошибки | `401`, `404` (в т.ч. файл чужой отправки) |
| Идемпотентность | безопасный |
| Лимиты | ≤ 8 MiB, ≤ 10 с |

### 3.7 `POST /api/v1/submissions/{id}/recognize`

| | |
|---|---|
| Назначение | Запустить OCR для загруженных изображений (асинхронно) |
| Доступ | submitter |
| Запрос | пустое тело или `{ "force": boolean }` (по умолчанию `false`) |
| Ответ | `202` + `Submission` (`status = recognizing`), если запуск начат; `200` + `Submission`, если запуск не потребовался (уже идёт, либо уже есть результат распознавания и `force = false`) |
| Ошибки | `401`, `403`, `404`, `409 INVALID_STATE` (в т.ч. `input_mode = "text"`; состояние `recognizing`/`evaluating`/`evaluated`), `429 RATE_LIMITED` |
| Валидация | `force` — boolean |
| Идемпотентность | по состоянию (см. 1.4) |
| Лимиты | ответ ≤ 2 с; фоновый OCR ≤ 60 с |

Успешный запуск создаёт новую транскрипцию (`source = "ocr"`, следующая версия) и переводит отправку в `ready_for_evaluation`. Неудача → `recognition_failed`, если текста ещё нет, иначе возврат в `ready_for_evaluation` (предыдущая версия сохраняется).
`force = true` требуется, чтобы заново распознать, когда распознавание уже удалось; новая версия **не** перезаписывает правки пользователя — она добавляется как следующая версия.

### 3.8 `GET /api/v1/submissions/{id}/transcription`

| | |
|---|---|
| Назначение | Получить текст ответа (для проверки OCR и правки) |
| Доступ | submitter, expert |
| Запрос | query `version` (целое ≥ 1; по умолчанию текущая) |
| Ответ 200 | `Transcription` |
| Ошибки | `401`, `404` (отправки нет, транскрипции ещё нет, либо такой версии нет) |
| Идемпотентность | безопасный |
| Лимиты | ≤ 5 с |

### 3.9 `PATCH /api/v1/submissions/{id}/transcription`

| | |
|---|---|
| Назначение | Исправить текст: создаёт **новую** версию, старые не изменяются |
| Доступ | submitter |
| Запрос | `{ "base_version": number, "text": string }` |
| Ответ 200 | `Transcription` (новая версия, `source = "user_edit"`, либо `"manual_input"` при `base_version = 0`) |
| Ошибки | `401`, `403`, `404`, `409 INVALID_STATE`, `409 TRANSCRIPTION_VERSION_CONFLICT`, `422 VALIDATION_ERROR` |
| Валидация | `base_version` = номер текущей версии (или `0`, если текста нет); `text` по тем же правилам и нормализации, что в `POST /submissions` |
| Идемпотентность | если нормализованный `text` равен текущему — `200` без новой версии |
| Лимиты | ≤ 5 с |

Допустимые состояния: `ready_for_recognition` и `recognition_failed` (только при `base_version = 0` — ручной ввод вместо OCR), `ready_for_evaluation`, `evaluation_failed`, `evaluated`. После новой версии статус становится `ready_for_evaluation`; прежняя оценка остаётся доступной с `is_current = false`.

### 3.10 `POST /api/v1/submissions/{id}/evaluate`

| | |
|---|---|
| Назначение | Запустить оценивание текущей транскрипции по критериям закреплённой конфигурации (асинхронно) |
| Доступ | submitter |
| Запрос | пустое тело или `{ "transcription_version": number }` (защита от гонок: должно совпадать с текущей версией) |
| Ответ | `202` + `Submission` (`status = evaluating`) при запуске; `200` + `Submission` если оценка этой версии уже идёт или уже успешна |
| Ошибки | `401`, `403`, `404`, `409 INVALID_STATE`, `409 TRANSCRIPTION_VERSION_CONFLICT`, `409 CONFIGURATION_NOT_APPROVED`, `429 RATE_LIMITED` (≥ 3 неудачи на эту версию), `429 DAILY_QUOTA_EXCEEDED` |
| Валидация | `transcription_version` ≥ 1 |
| Идемпотентность | по состоянию: на версию транскрипции — не более одной оценки в статусах `running`/`succeeded` |
| Лимиты | ответ ≤ 2 с; фоновое оценивание ≤ 90 с |

Конфигурация, критерии, профиль и модель берутся из закреплённой за отправкой конфигурации и фиксируются в оценке (`versions`). Передать другие версии нельзя; чтобы проверить по новой конфигурации, нужно создать новую отправку.

### 3.11 `GET /api/v1/submissions/{id}/result`

| | |
|---|---|
| Назначение | Результат: оценка, баллы по критериям, обоснования, доказательные фрагменты, версии, экспертное решение |
| Доступ | submitter, expert |
| Запрос | query `evaluation_id` (UUID; по умолчанию — последняя успешная) |
| Ответ 200 | `Evaluation` |
| Ошибки | `401`, `404` (отправки или указанной оценки нет), `409 RESULT_NOT_READY` (нет успешной оценки; `details.submission_status`) |
| Идемпотентность | безопасный; результат не пересчитывается и неизменен |
| Лимиты | ≤ 5 с |

### 3.12 `POST /api/v1/submissions/{id}/review-requests`

| | |
|---|---|
| Назначение | Попросить экспертную проверку оценки |
| Доступ | submitter |
| Запрос | `{ "evaluation_id": UUID \| null, "reason_code": "...", "criterion_codes": string[], "comment": string \| null }` |
| Ответ | `201` + `ReviewRequest`; `200` + существующий запрос (`Idempotent-Replay: true`), если на эту оценку он уже есть |
| Ошибки | `401`, `403`, `404`, `409 INVALID_STATE` (нет успешной оценки), `422 VALIDATION_ERROR` |
| Валидация | `evaluation_id`: `null` = последняя успешная; должна принадлежать этой отправке. `reason_code` из перечисления. `criterion_codes` — коды критериев этой оценки, без дублей. `comment` ≤ 1000 символов, управляющие символы удаляются |
| Идемпотентность | один запрос на оценку |
| Лимиты | ≤ 5 с |

### 3.13 `GET /api/v1/review-requests`

| | |
|---|---|
| Назначение | Очередь запросов для эксперта |
| Доступ | expert |
| Запрос | query `status` (`open` по умолчанию \| `resolved`), `limit`, `cursor` |
| Ответ 200 | `{ "items": ReviewRequestListItem[], "next_cursor": string \| null }` |
| Ошибки | `401`, `403` (токен отправки на экспертном маршруте), `422 VALIDATION_ERROR` |
| Идемпотентность | безопасный |
| Лимиты | ≤ 5 с |

```ts
interface ReviewRequestListItem {
  id: UUID; submission_id: UUID; evaluation_id: UUID;
  status: "open" | "resolved"; reason_code: ReviewRequest["reason_code"];
  total_score: number; max_score: number; needs_review: boolean;
  created_at: Timestamp;
}
```

Порядок: самые старые первыми.

### 3.14 `GET /api/v1/review-requests/{id}`

| | |
|---|---|
| Назначение | Детали запроса проверки; эксперт дальше читает `GET /submissions/{submission_id}`, `.../transcription?version=`, `.../result?evaluation_id=` и файлы со своим `X-Expert-Key` |
| Доступ | expert; submitter — только если запрос относится к его отправке |
| Ответ 200 | `ReviewRequest` (с `decision`, если есть) |
| Ошибки | `401`, `404` |
| Идемпотентность | безопасный |
| Лимиты | ≤ 5 с |

### 3.15 `POST /api/v1/review-requests/{id}/decision`

| | |
|---|---|
| Назначение | Вынести экспертное решение и закрыть запрос |
| Доступ | expert |
| Запрос | `{ "outcome": "confirmed" \| "adjusted", "criterion_adjustments": [ { "criterion_code": string, "score": number, "comment": string \| null } ], "comment": string }` |
| Ответ | `201` + `ExpertDecision`; `200` + существующее решение при повторе с тем же содержимым |
| Ошибки | `401`, `403`, `404`, `409 DECISION_ALREADY_EXISTS`, `422 VALIDATION_ERROR` |
| Валидация | `confirmed`: `criterion_adjustments` пуст. `adjusted`: непустой, коды из критериев оценки, без дублей, `0 ≤ score ≤ max_score` критерия, хотя бы одна корректировка меняет балл. `comment` обязателен, 1–2000 символов |
| Идемпотентность | одно решение на запрос |
| Лимиты | ≤ 5 с |

Сервер сам заполняет `original_score`, считает `final_total_score` тем же агрегатором, что и оценка (оригинальные баллы + корректировки) и ставит `decided_by` из метки ключа. Исходная `Evaluation` не изменяется; в `GET /result` появляются `final.source = "expert"` и вложенный `expert_review.decision`.

---

## 4. Правила изменения контракта

1. Добавление необязательного поля в ответ или нового маршрута — допустимо в `v1` с записью в CHANGELOG.md.
2. Переименование, удаление поля, смена типа, смысла или кода ошибки — только по согласованию и с записью в CHANGELOG.md; для несовместимых изменений используется `/api/v2`.
3. Pydantic-схемы в `backend/app/schemas/` обязаны точно воспроизводить этот документ. После реализации T-006 `openapi.json` экспортируется в `docs/openapi.json` и защищается snapshot-тестом.
4. Типы frontend генерируются из `openapi.json` (`openapi-typescript`), а не пишутся вручную.