import { Alert } from "../../components/Alert";
import { ConfidenceMeter } from "../../components/ConfidenceMeter";
import { Spinner } from "../../components/Spinner";
import { StatusBadge } from "../../components/StatusBadge";
import type { Evaluation, Submission } from "../../api/types";
import type { FlowError, FlowResultState } from "./useSubmissionFlow";
import { CriteriaList, flagLabel } from "./CriteriaList";
import { ReviewRequestForm } from "./ReviewRequestForm";
import type { RequestReviewPayload, ReviewRequest } from "../../api/types";

interface ResultStepProps {
  submission: Submission;
  resultState: FlowResultState;
  reviewRequest: ReviewRequest | null;
  reviewError: FlowError | null;
  busy: boolean;
  error: FlowError | null;
  onRetryResult: () => void;
  onDismissError: () => void;
  onBackToText: () => void;
  onStartOver: () => void;
  onRequestReview: (payload: RequestReviewPayload) => Promise<boolean>;
}

function downloadReport(evaluation: Evaluation) {
  const report = {
    generated_at: new Date().toISOString(),
    disclaimer: evaluation.disclaimer,
    evaluation,
  };
  const blob = new Blob([JSON.stringify(report, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `ai-exam-checker-result-${evaluation.id}.json`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

export function ResultStep({
  submission,
  resultState,
  reviewRequest,
  reviewError,
  busy,
  error,
  onRetryResult,
  onDismissError,
  onBackToText,
  onStartOver,
  onRequestReview,
}: ResultStepProps) {
  if (resultState.kind === "idle" || resultState.kind === "loading") {
    return (
      <section className="card" aria-busy="true" aria-labelledby="result-loading">
        <div className="progress-head">
          <Spinner />
          <div>
            <h2 className="card-title" id="result-loading">
              Загружаем результат…
            </h2>
            <p className="card-text" role="status">
              Оценка получена. Показываем баллы и обоснования.
            </p>
          </div>
        </div>
      </section>
    );
  }

  if (resultState.kind === "empty") {
    return (
      <section className="card" aria-labelledby="result-empty">
        <h2 className="card-title" id="result-empty">
          Результат не сформирован
        </h2>
        <Alert
          tone="warning"
          title="Оценка ещё недоступна"
          live="status"
          actions={
            <button type="button" className="button button-primary" onClick={onRetryResult}>
              Повторить загрузку
            </button>
          }
        >
          <p>
            {resultState.emptyMessage ??
              "Сервер не вернул результат. Проверьте статус отправки и повторите попытку."}
          </p>
        </Alert>
        <div className="form-actions">
          <button type="button" className="button button-secondary" onClick={onBackToText}>
            Вернуться к тексту
          </button>
        </div>
      </section>
    );
  }

  if (resultState.kind === "error" || !resultState.evaluation) {
    return (
      <section className="card" aria-labelledby="result-error">
        <h2 className="card-title" id="result-error">
          Не удалось загрузить результат
        </h2>
        <Alert
          tone="error"
          title={error?.title ?? "Ошибка загрузки результата"}
          live="alert"
          actions={
            <button type="button" className="button button-primary" onClick={onRetryResult}>
              Повторить
            </button>
          }
        >
          <p>{error?.message ?? "Повторите попытку."}</p>
        </Alert>
        <div className="form-actions">
          <button type="button" className="button button-secondary" onClick={onBackToText}>
            Вернуться к тексту
          </button>
        </div>
      </section>
    );
  }

  const evaluation = resultState.evaluation;
  const finalScore = evaluation.final.source === "expert" ? evaluation.final : null;
  const sortedCriteria = [...evaluation.criteria].sort((a, b) => a.position - b.position);
  const needsReview = evaluation.needs_review;

  return (
    <section className="step" aria-labelledby="result-title">
      <header className="result-header">
        <p className="badge">Предварительная оценка</p>
        <h2 className="page-title" id="result-title">
          Результат проверки
        </h2>
        {!evaluation.is_current && (
          <Alert tone="warning" title="Оценка относится к предыдущей версии текста" live="status">
            <p>
              Текст был изменён после оценивания. Запустите проверку заново, чтобы
              получить актуальный результат.
            </p>
          </Alert>
        )}
      </header>

      <section
        className={`card summary-card${needsReview ? " summary-card-review" : ""}`}
        aria-labelledby="summary-title"
      >
        <div className="summary-head">
          <h2 className="card-title" id="summary-title">
            Итог
          </h2>
          {needsReview ? (
            <StatusBadge tone="warning">Требуется проверка человеком</StatusBadge>
          ) : (
            <StatusBadge tone="success">Оценка сформирована</StatusBadge>
          )}
        </div>

        <div className="summary-metrics">
          <p className="score-total">
            <span className="score-value">{evaluation.final.total_score}</span>
            <span className="score-max">из {evaluation.final.max_score} баллов</span>
          </p>
          <div className="summary-meta">
            <p className="card-text">
              Источник итога:{" "}
              {evaluation.final.source === "expert"
                ? "решение эксперта"
                : "модель (предварительно)"}
              .
            </p>
            {finalScore && (
              <p className="card-text">
                Оценка модели: {evaluation.total_score} из {evaluation.max_score}.
              </p>
            )}
            <ConfidenceMeter
              value={evaluation.overall_confidence}
              label="Общая уверенность модели"
              level="overall"
            />
            <p className="confidence-disclaimer">
              Это самооценка модели, а не гарантия правильности ответа.
            </p>
          </div>
        </div>

        {evaluation.summary && <p className="summary-text">{evaluation.summary}</p>}

        <ul className="flag-list" aria-label="Пометки результата">
          {evaluation.flags.map((flag) => (
            <li key={flag}>
              <StatusBadge tone="warning">{flagLabel(flag)}</StatusBadge>
            </li>
          ))}
        </ul>

        {needsReview && (
          <Alert
            tone="warning"
            title="Результат может потребовать экспертной проверки"
            icon="!"
          >
            <p>
              Автоматическая система не уверена в корректности интерпретации
              текста или критерия. Этот статус не означает, что ответ неверный:
              проверьте логику и формулу оценки.
            </p>
          </Alert>
        )}

        <p className="disclaimer">{evaluation.disclaimer}</p>

        <div className="form-actions">
          <button
            type="button"
            className="button button-primary"
            onClick={() => downloadReport(evaluation)}
          >
            Скачать отчёт (JSON)
          </button>
          <button type="button" className="button button-secondary" onClick={onBackToText}>
            Вернуться к тексту
          </button>
          <button type="button" className="button button-ghost" onClick={onStartOver}>
            Новая проверка
          </button>
        </div>
      </section>

      {error && (
        <Alert
          tone="error"
          title={error.title}
          live="alert"
          actions={
            <button type="button" className="button button-secondary" onClick={onDismissError}>
              Закрыть
            </button>
          }
        >
          <p>{error.message}</p>
        </Alert>
      )}

      <CriteriaList criteria={sortedCriteria} />

      {evaluation.expert_review?.decision && (
        <ExpertDecisionBlock decision={evaluation.expert_review.decision} />
      )}

      <ReviewRequestForm
        evaluation={evaluation}
        criteria={sortedCriteria}
        review={reviewRequest ?? evaluation.expert_review}
        busy={busy}
        error={reviewError}
        onSubmit={onRequestReview}
      />

      <details className="card details provenance">
        <summary className="card-title">Версии оценивания</summary>
        <dl className="version-list">
          <div>
            <dt>Конфигурация</dt>
            <dd>
              {evaluation.versions.exam_configuration_id} (
              {evaluation.versions.exam_configuration_status})
            </dd>
          </div>
          <div>
            <dt>Экзамен</dt>
            <dd>
              {evaluation.versions.exam.code}, {evaluation.versions.exam.exam_year},{" "}
              версия {evaluation.versions.exam.version_label}
            </dd>
          </div>
          <div>
            <dt>Задание</dt>
            <dd>
              {evaluation.versions.task_version.task_number ?? "без номера"} (версия{" "}
              {evaluation.versions.task_version.version})
            </dd>
          </div>
          <div>
            <dt>Критерии</dt>
            <dd>версия {evaluation.versions.criteria_version.version}</dd>
          </div>
          <div>
            <dt>Профиль оценивания</dt>
            <dd>
              {evaluation.versions.evaluation_profile.code}, версия{" "}
              {evaluation.versions.evaluation_profile.version}
            </dd>
          </div>
          <div>
            <dt>Модель</dt>
            <dd>
              {evaluation.versions.model.provider} · запрошена{" "}
              {evaluation.versions.model.requested}
              {evaluation.versions.model.reported
                ? ` · ответила ${evaluation.versions.model.reported}`
                : ""}
            </dd>
          </div>
        </dl>
        {evaluation.versions.source_editions.length > 0 && (
          <ul className="prose-list">
            {evaluation.versions.source_editions.map((source) => (
              <li key={`${source.publisher}-${source.title}`}>
                {source.publisher}, «{source.title}», {source.edition_label}
                {source.url ? (
                  <>
                    {" — "}
                    <a href={source.url} rel="noreferrer noopener" target="_blank">
                      источник
                    </a>
                  </>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </details>

      <p className="footnote">
        Отправка {submission.id.slice(0, 8)}… · результат неизменяем. Повторная
        проверка создаётся заново.
      </p>
    </section>
  );
}

function ExpertDecisionBlock({ decision }: { decision: NonNullable<Evaluation["expert_review"]>["decision"] }) {
  if (!decision) return null;
  return (
    <section className="card expert-decision" aria-labelledby="expert-decision-title">
      <h2 className="card-title" id="expert-decision-title">
        Решение эксперта
      </h2>
      <p className="card-text">
        {decision.outcome === "confirmed"
          ? "Эксперт подтвердил оценку."
          : "Эксперт скорректировал оценку."}{" "}
        Итог: {decision.final_total_score} из {decision.max_score}.
      </p>
      {decision.criterion_adjustments.length > 0 && (
        <ul className="prose-list">
          {decision.criterion_adjustments.map((adjustment) => (
            <li key={adjustment.criterion_code}>
              {adjustment.criterion_code}: {adjustment.original_score} → {adjustment.score}
              {adjustment.comment ? ` — ${adjustment.comment}` : ""}
            </li>
          ))}
        </ul>
      )}
      <p className="card-text">{decision.comment}</p>
      <p className="footnote">
        Эксперт: {decision.decided_by} ·{" "}
        {new Date(decision.decided_at).toLocaleString("ru-RU")}
      </p>
    </section>
  );
}
