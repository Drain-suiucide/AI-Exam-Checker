import { useEffect, useMemo, useRef, useState } from "react";
import { Alert } from "../../components/Alert";
import { StatusBadge } from "../../components/StatusBadge";
import type { Submission, Transcription } from "../../api/types";
import type { SubmissionFlow } from "./useSubmissionFlow";

interface TranscriptionStepProps {
  submission: Submission;
  transcription: Transcription | null;
  transcriptionState: "idle" | "loading" | "ready" | "error";
  transcriptionError: SubmissionFlow["transcriptionError"];
  manualEntry: boolean;
  busy: SubmissionFlow["busy"];
  error: SubmissionFlow["error"];
  onRetry: () => void;
  onDismissError: () => void;
  onReloadTranscription: () => void;
  onSave: (text: string, baseVersion: number) => Promise<Transcription | null>;
  onEvaluate: (version: number) => void;
  onRecognize: () => void;
  onStartOver: () => void;
  onBackToResult: () => void;
  hasResult: boolean;
}

const SOURCE_LABEL: Record<Transcription["source"], string> = {
  ocr: "распознано автоматически",
  manual_input: "введено вручную",
  user_edit: "исправлено пользователем",
};

export function TranscriptionStep({
  submission,
  transcription,
  transcriptionState,
  transcriptionError,
  manualEntry,
  busy,
  error,
  onRetry,
  onDismissError,
  onReloadTranscription,
  onSave,
  onEvaluate,
  onRecognize,
  onStartOver,
  onBackToResult,
  hasResult,
}: TranscriptionStepProps) {
  const [draft, setDraft] = useState(transcription?.text ?? "");
  const [localError, setLocalError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const loadedVersion = transcription?.version ?? 0;

  useEffect(() => {
    setDraft(transcription?.text ?? "");
    setLocalError(null);
  }, [transcription?.id, transcription?.version, transcription?.text]);

  const dirty = draft !== (transcription?.text ?? "");
  const baseVersion = loadedVersion;
  const evaluationFailed = submission.status === "evaluation_failed";
  const evaluationError = submission.evaluation?.error ?? null;
  const isSaving = busy === "save";
  const isEvaluating = busy === "evaluate" || busy === "recognize";

  const lowConfidenceSegments = useMemo(() => {
    const segments = transcription?.ocr?.segments ?? [];
    const text = transcription?.text ?? "";
    return segments
      .filter((segment) => segment.confidence !== null && segment.confidence < 0.7)
      .map((segment) => ({
        ...segment,
        snippet: text.slice(segment.char_start, segment.char_end).trim(),
      }))
      .filter((segment) => segment.snippet.length > 0);
  }, [transcription]);

  const selectSegment = (start: number, end: number) => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.focus();
    textarea.setSelectionRange(start, end);
  };

  const handleSave = async () => {
    setLocalError(null);
    const normalized = draft.trim();
    if (normalized.length === 0) {
      setLocalError("Текст ответа не может быть пустым.");
      return;
    }
    await onSave(normalized, baseVersion);
  };

  const handleEvaluate = async () => {
    setLocalError(null);
    const normalized = draft.trim();
    if (normalized.length < 10) {
      setLocalError("Слишком короткий текст: минимум 10 символов после обрезки пробелов.");
      textareaRef.current?.focus();
      return;
    }
    let version = baseVersion;
    if (dirty || transcription === null) {
      const saved = await onSave(normalized, baseVersion);
      if (!saved) return;
      version = saved.version;
    }
    onEvaluate(version);
  };

  if (transcriptionState === "loading" && !transcription) {
    return (
      <section className="card" aria-labelledby="transcription-loading" aria-busy="true">
        <h2 className="card-title" id="transcription-loading">
          Загружаем распознанный текст…
        </h2>
        <p className="card-text" role="status">
          Текст ответа будет доступен для исправления сразу после загрузки.
        </p>
      </section>
    );
  }

  if (transcriptionState === "error" && !transcription) {
    return (
      <section className="card" aria-labelledby="transcription-error">
        <h2 className="card-title" id="transcription-error">
          Не удалось загрузить текст ответа
        </h2>
        <Alert
          tone="error"
          title={transcriptionError?.title ?? "Ошибка загрузки текста"}
          live="alert"
          actions={
            <button type="button" className="button button-primary" onClick={onReloadTranscription}>
              Повторить
            </button>
          }
        >
          <p>{transcriptionError?.message}</p>
        </Alert>
      </section>
    );
  }

  if (!transcription && !manualEntry) {
    return (
      <section className="card" aria-labelledby="transcription-empty">
        <h2 className="card-title" id="transcription-empty">
          Текст ответа ещё не готов
        </h2>
        <p className="card-text">
          Распознавание не завершено. Дождитесь результата или введите текст
          вручную.
        </p>
        <div className="form-actions">
          <button type="button" className="button button-primary" onClick={onRecognize}>
            Распознать текст
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="step" aria-labelledby="transcription-title">
      <div className="step-head">
        <h2 className="card-title" id="transcription-title">
          Проверьте распознанный текст
        </h2>
        <p className="card-text">
          Исправьте ошибки распознавания перед оценкой. Исправления влияют
          только на этот сценарий проверки.
        </p>
      </div>

      <div className="transcription-meta">
        {transcription ? (
          <>
            <StatusBadge tone="info">Версия {transcription.version}</StatusBadge>
            <StatusBadge tone="neutral">{SOURCE_LABEL[transcription.source]}</StatusBadge>
            <span className="meta-text">{transcription.char_count} символов</span>
          </>
        ) : (
          <StatusBadge tone="warning">Ручной ввод вместо распознавания</StatusBadge>
        )}
      </div>

      {lowConfidenceSegments.length > 0 && (
        <Alert tone="warning" title="Отдельные фрагменты распознаны с низкой уверенностью">
          <p>Проверьте эти места в тексте — они могут содержать ошибки.</p>
          <ul className="segment-list">
            {lowConfidenceSegments.map((segment) => (
              <li key={`${segment.index}-${segment.char_start}`}>
                <button
                  type="button"
                  className="segment-button"
                  onClick={() => selectSegment(segment.char_start, segment.char_end)}
                >
                  «{segment.snippet}»
                </button>
                <span className="meta-text">
                  уверенность {Math.round((segment.confidence ?? 0) * 100)}%
                </span>
              </li>
            ))}
          </ul>
        </Alert>
      )}

      <div className="field">
        <label className="label" htmlFor="transcription-text">
          Текст ответа
        </label>
        <p className="field-hint">
          Редактируемый текст. Содержимое отображается как обычный текст, без
          форматирования.
        </p>
        <textarea
          id="transcription-text"
          ref={textareaRef}
          className="textarea textarea-large"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          rows={12}
          aria-describedby="transcription-hint"
          aria-invalid={Boolean(localError)}
        />
        <p className="field-hint" id="transcription-hint">
          {dirty
            ? "Есть несохранённые изменения — они будут сохранены перед запуском проверки."
            : "Изменений нет."}
        </p>
        {localError && (
          <p className="field-error" role="alert">
            {localError}
          </p>
        )}
      </div>

      {evaluationFailed && (
        <Alert
          tone="error"
          title="Оценивание не завершилось"
          live="alert"
          actions={
            <button type="button" className="button button-primary" onClick={() => void handleEvaluate()}>
              Повторить оценивание
            </button>
          }
        >
          <p>
            {evaluationError?.message ??
              "Сервер не смог оценить ответ. Проверьте текст и конфигурацию."}
            {evaluationError?.code ? ` (код: ${evaluationError.code})` : ""}
          </p>
        </Alert>
      )}

      {error && (
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

      <div className="toolbar" role="group" aria-label="Действия с текстом">
        <button
          type="button"
          className="button button-secondary"
          onClick={() => void handleSave()}
          disabled={busy !== null || (!dirty && transcription !== null)}
        >
          {isSaving ? "Сохраняем…" : "Сохранить исправления"}
        </button>
        <button
          type="button"
          className="button button-ghost"
          onClick={() => {
            setDraft(transcription?.text ?? "");
            setLocalError(null);
          }}
          disabled={busy !== null || !dirty}
        >
          Отменить правки
        </button>
        <button
          type="button"
          className="button button-ghost"
          onClick={onReloadTranscription}
          disabled={busy !== null}
        >
          Перезагрузить текст
        </button>
      </div>

      <div className="form-actions">
        <button
          type="button"
          className="button button-primary button-large"
          onClick={() => void handleEvaluate()}
          disabled={busy !== null}
        >
          {isEvaluating ? "Запускаем проверку…" : "Запустить проверку"}
        </button>
        {submission.input_mode === "image" && (
          <button
            type="button"
            className="button button-secondary"
            onClick={onRecognize}
            disabled={busy !== null}
          >
            Распознать заново
          </button>
        )}
        {hasResult && (
          <button type="button" className="button button-secondary" onClick={onBackToResult}>
            Вернуться к результату
          </button>
        )}
        <button type="button" className="button button-ghost" onClick={onStartOver} disabled={busy !== null}>
          Начать заново
        </button>
      </div>

      <p className="footnote">
        Оценка предварительная и не заменяет экспертную проверку.
      </p>
    </section>
  );
}
