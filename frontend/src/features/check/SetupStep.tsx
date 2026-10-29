import { useMemo, useState } from "react";
import type { FormEvent } from "react";
import { Alert } from "../../components/Alert";
import { FileDropZone, validateFiles } from "../../components/FileDropZone";
import { StatusBadge } from "../../components/StatusBadge";
import type { CreateSubmissionInput } from "../../api/checkApi";
import type { ExamConfiguration } from "../../api/types";
import type { SubmissionFlow } from "./useSubmissionFlow";

type InputMode = "text" | "image";

interface SetupStepProps {
  configs: ExamConfiguration[];
  configsState: "loading" | "ready" | "error";
  configsError: SubmissionFlow["configsError"];
  selectedConfig: ExamConfiguration | null;
  onSelectConfig: (id: string) => void;
  onReloadConfigs: () => void;
  onSubmit: (input: CreateSubmissionInput) => void;
  busy: boolean;
  error: SubmissionFlow["error"];
  onRetry: () => void;
  onDismissError: () => void;
}

export function SetupStep({
  configs,
  configsState,
  configsError,
  selectedConfig,
  onSelectConfig,
  onReloadConfigs,
  onSubmit,
  busy,
  error,
  onRetry,
  onDismissError,
}: SetupStepProps) {
  const [mode, setMode] = useState<InputMode>("text");
  const [text, setText] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [origin, setOrigin] = useState<"synthetic" | "anonymized" | "">("");
  const [localErrors, setLocalErrors] = useState<Record<string, string>>({});

  const limits = selectedConfig?.limits;
  const trimmedLength = text.trim().length;
  const counterId = useMemo(() => "answer-counter", []);

  if (configsState === "loading") {
    return (
      <section className="card" aria-labelledby="setup-loading" aria-busy="true">
        <h2 className="card-title" id="setup-loading">
          Доступные конфигурации
        </h2>
        <p className="card-text" role="status">
          Загружаем список подтверждённых конфигураций…
        </p>
      </section>
    );
  }

  if (configsState === "error") {
    return (
      <section className="card" aria-labelledby="setup-error">
        <h2 className="card-title" id="setup-error">
          Доступные конфигурации
        </h2>
        <Alert
          tone="error"
          title={configsError?.title ?? "Не удалось загрузить конфигурации"}
          live="alert"
          actions={
            <button type="button" className="button button-primary" onClick={onReloadConfigs}>
              Повторить
            </button>
          }
        >
          <p>{configsError?.message}</p>
        </Alert>
      </section>
    );
  }

  if (configs.length === 0) {
    return (
      <section className="card" aria-labelledby="setup-empty">
        <h2 className="card-title" id="setup-empty">
          Нет доступных конфигураций
        </h2>
        <p className="card-text">
          Подтверждённых конфигураций экзамена пока нет. В исследовательском
          MVP используются только подтверждённые варианты проверки; иные
          предметы и задания временно недоступны.
        </p>
        <button type="button" className="button button-secondary" onClick={onReloadConfigs}>
          Обновить список
        </button>
      </section>
    );
  }

  const validate = (): Record<string, string> => {
    const next: Record<string, string> = {};
    if (!selectedConfig) next.config = "Выберите конфигурацию экзамена.";
    if (!origin) next.data_origin = "Подтвердите, что в ответе нет персональных данных.";
    if (!limits) return next;

    if (mode === "text") {
      if (trimmedLength === 0) next.text = "Введите текст ответа.";
      else if (trimmedLength < limits.min_answer_chars)
        next.text = `Минимум ${limits.min_answer_chars} символов. Сейчас ${trimmedLength}.`;
      else if (trimmedLength > limits.max_answer_chars)
        next.text = `Максимум ${limits.max_answer_chars} символов. Сейчас ${trimmedLength}.`;
    } else {
      const issues = validateFiles(files, limits);
      if (issues.length > 0) {
        next.files = issues.map((issue) => issue.message).join(" ");
      }
    }
    return next;
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const issues = validate();
    setLocalErrors(issues);
    if (Object.keys(issues).length > 0 || !selectedConfig || !origin) return;

    if (mode === "text") {
      onSubmit({
        examConfigurationId: selectedConfig.id,
        dataOrigin: origin,
        inputMode: "text",
        text: text.trim(),
      });
    } else {
      onSubmit({
        examConfigurationId: selectedConfig.id,
        dataOrigin: origin,
        inputMode: "image",
        files,
      });
    }
  };

  const serverFields = error?.fields ?? {};
  const showFieldError = (key: string) => localErrors[key] ?? serverFields[key];

  return (
    <form className="check-form" onSubmit={handleSubmit} noValidate>
      {error && !error.fields.text && !error.fields.files && (
        <Alert
          tone="error"
          title={error.title}
          live="alert"
          actions={
            <div className="alert-actions">
              {error.retryable && (
                <button type="button" className="button button-primary" onClick={onRetry}>
                  Повторить
                </button>
              )}
              <button type="button" className="button button-secondary" onClick={onDismissError}>
                Закрыть
              </button>
            </div>
          }
        >
          <p>{error.message}</p>
        </Alert>
      )}

      <section className="card" aria-labelledby="config-title">
        <h2 className="card-title" id="config-title">
          1. Конфигурация экзамена
        </h2>
        <p className="card-text">
          Доступны только подтверждённые конфигурации. Иные предметы и задания
          временно недоступны.
        </p>
        <fieldset className="field-group" aria-describedby="config-note">
          <legend className="label">Конфигурация</legend>
          <div className="config-options">
            {configs.map((config) => (
              <label
                key={config.id}
                className={`config-option${config.id === selectedConfig?.id ? " config-option-selected" : ""}`}
              >
                <input
                  type="radio"
                  name="exam_configuration_id"
                  value={config.id}
                  checked={config.id === selectedConfig?.id}
                  onChange={() => onSelectConfig(config.id)}
                />
                <span className="config-option-body">
                  <span className="config-option-title">
                    {config.exam.title} · {config.exam.exam_year}
                  </span>
                  <span className="config-option-meta">
                    Задание {config.task.task_number ?? "без номера"} «
                    {config.task.title}» · {config.criteria_version.criteria.length} критерий(ев) ·{" "}
                    макс. {config.criteria_version.max_score_total} балл(ов)
                  </span>
                </span>
                <StatusBadge tone="success">Подтверждена</StatusBadge>
              </label>
            ))}
          </div>
          <p className="field-hint" id="config-note">
            Конфигурация фиксирует версии задания и критериев: изменить их внутри
            проверки нельзя.
          </p>
        </fieldset>
        {showFieldError("config") && (
          <p className="field-error">{showFieldError("config")}</p>
        )}

        {selectedConfig && (
          <div className="task-summary">
            <h3 className="subtitle">Задание</h3>
            <p className="card-text">{selectedConfig.task.statement}</p>
            <details className="details">
              <summary>Критерии предварительного оценивания</summary>
              <ol className="prose-list">
                {selectedConfig.criteria_version.criteria
                  .slice()
                  .sort((a, b) => a.position - b.position)
                  .map((criterion) => (
                    <li key={criterion.id}>
                      <strong>{criterion.code}</strong> · {criterion.title} (макс.{" "}
                      {criterion.max_score}) — {criterion.description}
                    </li>
                  ))}
              </ol>
            </details>
          </div>
        )}
      </section>

      <section className="card" aria-labelledby="input-title">
        <h2 className="card-title" id="input-title">
          2. Ответ
        </h2>
        <fieldset className="field-group">
          <legend className="label">Способ ввода</legend>
          <div className="segmented" role="radiogroup" aria-label="Способ ввода ответа">
            <label className={`segmented-option${mode === "text" ? " segmented-selected" : ""}`}>
              <input
                type="radio"
                name="input_mode"
                value="text"
                checked={mode === "text"}
                onChange={() => setMode("text")}
              />
              Ввести текст
            </label>
            <label className={`segmented-option${mode === "image" ? " segmented-selected" : ""}`}>
              <input
                type="radio"
                name="input_mode"
                value="image"
                checked={mode === "image"}
                onChange={() => setMode("image")}
              />
              Загрузить изображение
            </label>
          </div>
        </fieldset>

        {mode === "text" ? (
          <div className="field">
            <label className="label" htmlFor="answer-text">
              Текст ответа
            </label>
            <textarea
              id="answer-text"
              className="textarea"
              value={text}
              onChange={(event) => setText(event.target.value)}
              rows={8}
              required
              aria-required="true"
              aria-describedby={`${counterId} answer-hint`}
              aria-invalid={Boolean(showFieldError("text"))}
              placeholder="Вставьте или введите развёрнутый ответ ученика"
              maxLength={limits ? limits.max_answer_chars : undefined}
            />
            <p className="field-hint" id="answer-hint">
              Для тестов используйте синтетические или обезличенные примеры.
            </p>
            {limits && (
              <p
                className={`field-counter${trimmedLength > limits.max_answer_chars ? " field-counter-over" : ""}`}
                id={counterId}
              >
                {trimmedLength} / {limits.max_answer_chars} символов (минимум{" "}
                {limits.min_answer_chars})
              </p>
            )}
            {showFieldError("text") && (
              <p className="field-error" role="alert">
                {showFieldError("text")}
              </p>
            )}
          </div>
        ) : (
          <div className="field">
            {limits && (
              <FileDropZone
                files={files}
                onChange={setFiles}
                maxFiles={limits.max_files}
                maxFileBytes={limits.max_file_bytes}
                allowedMimeTypes={limits.allowed_mime_types}
                disabled={busy}
              />
            )}
            <p className="field-hint">
              Файл проверяется в браузере для удобства, но окончательную
              проверку типа и размера выполняет сервер.
            </p>
            {showFieldError("files") && (
              <p className="field-error" role="alert">
                {showFieldError("files")}
              </p>
            )}
          </div>
        )}
      </section>

      <section className="card" aria-labelledby="origin-title">
        <h2 className="card-title" id="origin-title">
          3. Данные ответа
        </h2>
        <fieldset
          className="field-group"
          aria-describedby="origin-hint"
          aria-invalid={Boolean(showFieldError("data_origin"))}
        >
          <legend className="label">
            Подтверждение происхождения данных <span aria-hidden="true">*</span>
          </legend>
          <p className="field-hint" id="origin-hint">
            Не загружайте реальные персональные данные обучающихся. Выберите
            подходящий вариант.
          </p>
          <label className="check-option">
            <input
              type="radio"
              name="data_origin"
              value="synthetic"
              checked={origin === "synthetic"}
              onChange={() => setOrigin("synthetic")}
            />
            Синтетический ответ (создан для теста)
          </label>
          <label className="check-option">
            <input
              type="radio"
              name="data_origin"
              value="anonymized"
              checked={origin === "anonymized"}
              onChange={() => setOrigin("anonymized")}
            />
            Обезличенный пример (персональные данные удалены)
          </label>
          {showFieldError("data_origin") && (
            <p className="field-error" role="alert">
              {showFieldError("data_origin")}
            </p>
          )}
        </fieldset>
      </section>

      <div className="form-actions">
        <button type="submit" className="button button-primary button-large" disabled={busy}>
          {busy ? "Отправляем…" : "Далее"}
        </button>
        {busy && (
          <span className="form-status" role="status">
            Создаём отправку…
          </span>
        )}
      </div>
    </form>
  );
}
