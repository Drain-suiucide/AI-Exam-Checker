import { useId, useState } from "react";
import type { FormEvent } from "react";
import { Alert } from "../../components/Alert";
import { StatusBadge } from "../../components/StatusBadge";
import type {
  CriterionResult,
  Evaluation,
  RequestReviewPayload,
  ReviewReasonCode,
  ReviewRequest,
} from "../../api/types";
import type { FlowError } from "./useSubmissionFlow";

const REASONS: { value: ReviewReasonCode; label: string }[] = [
  { value: "disagree_with_score", label: "Не согласен с баллом по критерию" },
  { value: "ocr_error", label: "Ошибка распознавания исказила ответ" },
  { value: "unclear_rationale", label: "Обоснование непонятно" },
  { value: "other", label: "Другая причина" },
];

interface ReviewRequestFormProps {
  evaluation: Evaluation;
  criteria: CriterionResult[];
  review: ReviewRequest | null;
  busy: boolean;
  error: FlowError | null;
  onSubmit: (payload: RequestReviewPayload) => Promise<boolean>;
}

const MAX_COMMENT = 1000;

export function ReviewRequestForm({
  evaluation,
  criteria,
  review,
  busy,
  error,
  onSubmit,
}: ReviewRequestFormProps) {
  const idPrefix = useId();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState<ReviewReasonCode | "">("");
  const [codes, setCodes] = useState<string[]>([]);
  const [comment, setComment] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);

  if (review) {
    const resolved = review.status === "resolved";
    return (
      <section className="card review-card" aria-labelledby={`${idPrefix}-review-status`}>
        <div className="review-head">
          <h2 className="card-title" id={`${idPrefix}-review-status`}>
            Экспертная проверка
          </h2>
          <StatusBadge tone={resolved ? "success" : "warning"}>
            {resolved ? "Запрос проверки закрыт" : "Запрос на проверку отправлен"}
          </StatusBadge>
        </div>
        <p className="card-text" role="status">
          {resolved
            ? "Эксперт рассмотрел запрос. Решение показано в блоке результата."
            : "Запрос получен. Автоматический результат остаётся предварительным до решения эксперта."}
        </p>
      </section>
    );
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!reason) {
      setLocalError("Выберите причину запроса.");
      return;
    }
    setLocalError(null);
    await onSubmit({
      evaluation_id: evaluation.id,
      reason_code: reason,
      criterion_codes: codes,
      comment: comment.trim() ? comment.trim() : null,
    });
  };

  return (
    <section className="card" aria-labelledby={`${idPrefix}-review-title`}>
      <div className="review-head">
        <h2 className="card-title" id={`${idPrefix}-review-title`}>
          Нужна проверка эксперта?
        </h2>
        {!open && (
          <button type="button" className="button button-secondary" onClick={() => setOpen(true)}>
            Запросить экспертную проверку
          </button>
        )}
      </div>
      <p className="card-text">
        Автоматическая оценка предварительная. Если результат спорный, отправьте
        запрос — он не означает, что ответ неверный.
      </p>

      {open && (
        <form className="review-form" onSubmit={handleSubmit} noValidate>
          <div className="field">
            <label className="label" htmlFor={`${idPrefix}-reason`}>
              Причина запроса <span aria-hidden="true">*</span>
            </label>
            <select
              id={`${idPrefix}-reason`}
              className="select"
              value={reason}
              required
              aria-required="true"
              aria-invalid={Boolean(localError)}
              onChange={(event) => setReason(event.target.value as ReviewReasonCode)}
            >
              <option value="">Выберите причину</option>
              {REASONS.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
            {localError && (
              <p className="field-error" role="alert">
                {localError}
              </p>
            )}
          </div>

          <fieldset className="field-group">
            <legend className="label">Спорные критерии</legend>
            <p className="field-hint">
              Ничего не выбирайте, если спорна вся оценка.
            </p>
            {criteria.map((criterion) => (
              <label className="check-option" key={criterion.code}>
                <input
                  type="checkbox"
                  value={criterion.code}
                  checked={codes.includes(criterion.code)}
                  onChange={(event) =>
                    setCodes((current) =>
                      event.target.checked
                        ? [...current, criterion.code]
                        : current.filter((code) => code !== criterion.code),
                    )
                  }
                />
                {criterion.code} — {criterion.title}
              </label>
            ))}
          </fieldset>

          <div className="field">
            <label className="label" htmlFor={`${idPrefix}-comment`}>
              Комментарий
            </label>
            <textarea
              id={`${idPrefix}-comment`}
              className="textarea"
              rows={4}
              value={comment}
              maxLength={MAX_COMMENT}
              onChange={(event) => setComment(event.target.value)}
              aria-describedby={`${idPrefix}-comment-hint`}
            />
            <p className="field-hint" id={`${idPrefix}-comment-hint`}>
              Не указывайте персональные данные. {comment.length} / {MAX_COMMENT}
            </p>
          </div>

          {error && (
            <Alert tone="error" title={error.title} live="alert">
              <p>{error.message}</p>
            </Alert>
          )}

          <div className="form-actions">
            <button type="submit" className="button button-primary" disabled={busy}>
              {busy ? "Отправляем…" : "Отправить запрос"}
            </button>
            <button
              type="button"
              className="button button-secondary"
              onClick={() => {
                setOpen(false);
                setLocalError(null);
              }}
              disabled={busy}
            >
              Отмена
            </button>
          </div>
        </form>
      )}
    </section>
  );
}
