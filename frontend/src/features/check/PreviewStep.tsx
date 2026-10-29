import { useCallback } from "react";
import { Alert } from "../../components/Alert";
import { formatBytes } from "../../components/FileDropZone";
import { useObjectUrl } from "../../hooks/useObjectUrl";
import type { CheckApi } from "../../api/checkApi";
import type { FileInfo, Submission } from "../../api/types";
import type { SubmissionFlow } from "./useSubmissionFlow";

interface PreviewStepProps {
  api: CheckApi;
  submission: Submission;
  token: string;
  busy: boolean;
  error: SubmissionFlow["error"];
  onRecognize: () => void;
  onRetry: () => void;
  onDismissError: () => void;
  onManualEntry: () => void;
  onStartOver: () => void;
}

function PagePreview({
  api,
  submissionId,
  token,
  file,
  index,
  total,
}: {
  api: CheckApi;
  submissionId: string;
  token: string;
  file: FileInfo;
  index: number;
  total: number;
}) {
  const load = useCallback(
    (signal: AbortSignal) => api.getFileBlob(submissionId, token, file.id, signal),
    [api, submissionId, token, file.id],
  );
  const state = useObjectUrl(load);

  return (
    <figure className="page-preview">
      <figcaption className="page-preview-caption">
        Страница {index + 1} из {total}
      </figcaption>
      {state.status === "loading" && (
        <div className="image-placeholder" role="status">
          Загружаем изображение…
        </div>
      )}
      {state.status === "error" && (
        <div className="image-placeholder image-placeholder-error">
          Не удалось показать изображение. Оно загружено на сервер, но предпросмотр
          недоступен.
        </div>
      )}
      {state.status === "ready" && state.url && (
        <img
          className="page-image"
          src={state.url}
          alt={`Предпросмотр ответа, страница ${index + 1}`}
        />
      )}
    </figure>
  );
}

export function PreviewStep({
  api,
  submission,
  token,
  busy,
  error,
  onRecognize,
  onRetry,
  onDismissError,
  onManualEntry,
  onStartOver,
}: PreviewStepProps) {
  const recognitionFailed = submission.status === "recognition_failed";
  const recognitionError = submission.recognition?.error ?? null;

  return (
    <section className="step" aria-labelledby="preview-title">
      <div className="step-head">
        <h2 className="card-title" id="preview-title">
          Проверьте изображение перед распознаванием
        </h2>
        <p className="card-text">
          Скан ответа будет распознан автоматически. Если загружен не тот файл,
          замените его — начните проверку заново.
        </p>
      </div>

      <div className="page-preview-grid">
        {submission.files.map((file, index) => (
          <PagePreview
            key={file.id}
            api={api}
            submissionId={submission.id}
            token={token}
            file={file}
            index={index}
            total={submission.files.length}
          />
        ))}
      </div>

      <ul className="meta-list" aria-label="Сведения о файлах">
        {submission.files.map((file) => (
          <li key={file.id}>
            Страница {file.page_index + 1}: {file.mime_type}, {formatBytes(file.size_bytes)},{" "}
            {file.width_px}×{file.height_px} px
          </li>
        ))}
      </ul>

      {recognitionFailed && (
        <Alert
          tone="error"
          title="Не удалось распознать текст"
          live="alert"
          actions={
            <>
              <button type="button" className="button button-primary" onClick={onRecognize} disabled={busy}>
                Повторить распознавание
              </button>
              <button type="button" className="button button-secondary" onClick={onManualEntry}>
                Ввести текст вручную
              </button>
            </>
          }
        >
          <p>
            {recognitionError?.message ??
              "Сервис распознавания не вернул текст. Проверьте качество скана или введите текст вручную."}
            {recognitionError?.code ? ` (код: ${recognitionError.code})` : ""}
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

      <div className="form-actions">
        <button
          type="button"
          className="button button-primary button-large"
          onClick={onRecognize}
          disabled={busy}
        >
          {busy ? "Запускаем распознавание…" : "Распознать текст"}
        </button>
        <button type="button" className="button button-secondary" onClick={onStartOver}>
          Заменить файл
        </button>
        {busy && (
          <span className="form-status" role="status">
            Отправляем задачу распознавания…
          </span>
        )}
      </div>

      <p className="footnote">
        Проверка не сохраняет реальные данные обучающихся. При обновлении
        страницы доступ к отправке будет потерян.
      </p>
    </section>
  );
}
