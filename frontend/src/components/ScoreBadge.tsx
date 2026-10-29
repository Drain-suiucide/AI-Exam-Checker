interface ScoreBadgeProps {
  score: number;
  maxScore: number;
}

/** Балл с текстовой расшифровкой: «1 из 1 балла». */
export function ScoreBadge({ score, maxScore }: ScoreBadgeProps) {
  const tone = score >= maxScore ? "full" : score === 0 ? "zero" : "partial";
  return (
    <span className={`score-badge score-badge-${tone}`}>
      {score} из {maxScore}
    </span>
  );
}
