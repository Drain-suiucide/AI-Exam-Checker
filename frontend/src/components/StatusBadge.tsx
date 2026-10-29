import type { ReactNode } from "react";

export type BadgeTone = "neutral" | "info" | "success" | "warning" | "error";

interface StatusBadgeProps {
  tone?: BadgeTone;
  children: ReactNode;
}

/** Бейдж статуса: всегда содержит текст, цвет — только вспомогательный признак. */
export function StatusBadge({ tone = "neutral", children }: StatusBadgeProps) {
  return <span className={`status-badge status-badge-${tone}`}>{children}</span>;
}
