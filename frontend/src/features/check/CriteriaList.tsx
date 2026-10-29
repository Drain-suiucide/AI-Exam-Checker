import { ConfidenceMeter } from "../../components/ConfidenceMeter";
import { ScoreBadge } from "../../components/ScoreBadge";
import { StatusBadge } from "../../components/StatusBadge";
import type { CriterionResult, EvidenceRef, Flag } from "../../api/types";

const FLAG_LABEL: Record<Flag, string> = {
  LOW_CONFIDENCE: "Низкая уверенность",
  NO_EVIDENCE_FOUND: "Не найден подтверждающий фрагмент",
  AMBIGUOUS: "Спорная интерпретация",
  OCR_LOW_QUALITY: "Низкое качество распознавания",
};

export function flagLabel(flag: Flag): string {
  return FLAG_LABEL[flag] ?? flag;
}

function EvidenceBlock({ evidence }: { evidence: EvidenceRef }) {
  return (
    <li className={`evidence evidence-${evidence.kind}`}>
      <div className="evidence-head">
        <StatusBadge tone={evidence.kind === "supports" ? "success" : "warning"}>
          {evidence.kind === "supports" ? "Подтверждает балл" : "Ошибка или пробел"}
        </StatusBadge>
        <span className="evidence-range">
          символы {evidence.char_start}–{evidence.char_end}
        </span>
      </div>
      <blockquote className="evidence-quote">{evidence.quote}</blockquote>
      {evidence.note && <p className="evidence-note">{evidence.note}</p>}
    </li>
  );
}

interface CriteriaListProps {
  criteria: CriterionResult[];
}

/**
 * Баллы по критериям с обоснованием и фрагментами ответа.
 * Каждый критерий — элемент списка с семантическим заголовком.
 */
export function CriteriaList({ criteria }: CriteriaListProps) {
  if (criteria.length === 0) {
    return (
      <section className="card" aria-labelledby="criteria-empty">
        <h2 className="card-title" id="criteria-empty">
          Баллы по критериям
        </h2>
        <p className="card-text" role="status">
          Сервер не вернул ни одного критерия. Результат неполный — проверьте
          его у эксперта или повторите оценивание.
        </p>
      </section>
    );
  }

  return (
    <section className="criteria-section" aria-labelledby="criteria-title">
      <h2 className="card-title" id="criteria-title">
        Баллы по критериям
      </h2>
      <ol className="criteria-list">
        {criteria.map((criterion) => (
          <li className="card criterion" key={criterion.criterion_id}>
            <div className="criterion-head">
              <h3 className="criterion-title">
                <span className="criterion-code">{criterion.code}</span>
                {criterion.title}
              </h3>
              <ScoreBadge score={criterion.score} maxScore={criterion.max_score} />
            </div>

            <ConfidenceMeter
              value={criterion.confidence}
              label="Уверенность модели по критерию"
            />
            <p className="confidence-disclaimer">
              Уверенность — самооценка модели, а не вероятность правильности.
            </p>

            {criterion.flags.length > 0 && (
              <ul className="flag-list" aria-label="Пометки по критерию">
                {criterion.flags.map((flag) => (
                  <li key={flag}>
                    <StatusBadge tone="warning">{flagLabel(flag)}</StatusBadge>
                  </li>
                ))}
              </ul>
            )}

            <div className="criterion-body">
              <h4 className="subtitle">Почему это оценено так</h4>
              <p className="criterion-rationale">{criterion.rationale}</p>
              {criterion.uncertainty_note && (
                <p className="criterion-uncertainty">
                  <strong>Спорное место:</strong> {criterion.uncertainty_note}
                </p>
              )}
            </div>

            <div className="criterion-evidence">
              <h4 className="subtitle">Фрагменты ответа</h4>
              {criterion.evidence.length === 0 ? (
                <p className="card-text">
                  Подтверждающих фрагментов не найдено.
                </p>
              ) : (
                <ul className="evidence-list">
                  {criterion.evidence.map((evidence) => (
                    <EvidenceBlock key={evidence.id} evidence={evidence} />
                  ))}
                </ul>
              )}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
