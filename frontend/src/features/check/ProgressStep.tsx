import { Alert } from "../../components/Alert";
import { Spinner } from "../../components/Spinner";
import type { Submission } from "../../api/types";
import type { SubmissionFlow } from "./useSubmissionFlow";

interface ProgressStepProps {
  submission: Submission;
  isSlow: boolean;
  pollError: SubmissionFlow["pollError"];
  onRefresh: () => void;
}

/**
 * Ожидание фоновой обработки. Прогресс не выдумывается: показывается статус
 * сервера и подсказка, если ответ долгий.
 */
export function ProgressStep({ submission, isSlow, pollError, onRefresh }: ProgressStepProps) {
  const recognizing = submission.status === "recognizing";
  const recognitionAttempt = submission.recognition?.attempt_no;
  const evaluationAttempt = submission.evaluation?.attempt_no;
  const startedAt = recognizing
    ? submission.recognition?.started_at
    : submission.evaluation?.started_at;

  return (
    <section className="card progress-card" aria-labelledby="progress-title" aria-busy="true">
      <div className="progress-head">
        <Spinner />
        <div>
          <h2 className="card-title" id="progress-title">
            {recognizing ? "Распознаём текст и проверяем ответ…" : "Оцениваем ответ по критериям…"}
          </h2>
          <p className="card-text" role="status" aria-live="polite">
            {recognizing
              ? "Скан обрабатывается автоматически. Обычно это занимает до минуты."
              : "Сервер оценивает текст по подтверждённым критериям. Обычно это занимает до полутора минут."}
          </p>
        </div>
      </div>

      <dl className="progress-meta">
        <div>
          <dt>Этап</dt>
          <dd>{recognizing ? "Распознавание (OCR)" : "Оценивание"}</dd>
        </div>
        {typeof (recognizing ? recognitionAttempt : evaluationAttempt) === "number" && (
          <div>
            <dt>Попытка</dt>
            <dd>{recognizing ? recognitionAttempt : evaluationAttempt}</dd>
          </div>
        )}
        {startedAt && (
          <div>
            <dt>Начато</dt>
            <dd>{new Date(startedAt).toLocaleTimeString("ru-RU")}</dd>
          </div>
        )}
      </dl>

      {isSlow && (
        <Alert tone="warning" title="Обработка занимает больше обычного" live="status">
          <p>
            Можно подождать или повторить запрос статуса. Не закрывайте вкладку,
            пока обработка не завершится.
          </p>
        </Alert>
      )}

      {pollError && (
        <Alert
          tone="error"
          title={pollError.title}
          live="alert"
          actions={
            <button type="button" className="button button-primary" onClick={onRefresh}>
              Повторить запрос статуса
            </button>
          }
        >
          <p>{pollError.message}</p>
        </Alert>
      )}

      <p className="footnote">
        Страница автоматически обновляет статус каждые{" "}
        {Math.round((submission.poll_interval_ms ?? 2000) / 1000)} с.
      </p>
    </section>
  );
}
