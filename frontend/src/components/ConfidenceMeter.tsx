interface ConfidenceMeterProps {
  /** Самооценка модели 0.00–1.00 (API_CONTRACT §1). */
  value: number;
  label: string;
  level?: "criterion" | "overall";
}

/**
 * Уверенность модели. Показывается текстом и полосой, но не как вероятность
 * правильности: рядом всегда есть пояснение.
 */
export function ConfidenceMeter({ value, label, level = "criterion" }: ConfidenceMeterProps) {
  const clamped = Math.max(0, Math.min(1, value));
  const percent = Math.round(clamped * 100);
  const low = clamped < 0.5;
  return (
    <div className={`confidence confidence-${level}`}>
      <div className="confidence-head">
        <span className="confidence-label">{label}</span>
        <span className="confidence-value">
          {percent}%{low ? " · низкая" : ""}
        </span>
      </div>
      <div
        className="confidence-track"
        role="progressbar"
        aria-label={`${label}: ${percent}%`}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
      >
        <span
          className={`confidence-fill${low ? " confidence-fill-low" : ""}`}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
