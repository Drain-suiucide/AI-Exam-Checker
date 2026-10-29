import type { ReactNode } from "react";

export type AlertTone = "info" | "warning" | "error" | "success";

interface AlertProps {
  tone?: AlertTone;
  title: string;
  children?: ReactNode;
  /** role="alert" объявляется экранному диктору сразу; для неспешных сообщений — "status". */
  live?: "alert" | "status" | "off";
  actions?: ReactNode;
  icon?: string;
}

const TONE_ICON: Record<AlertTone, string> = {
  info: "i",
  warning: "!",
  error: "×",
  success: "✓",
};

/**
 * Inline-уведомление. Содержит текстовую метку тона, поэтому состояние не
 * различается только цветом (docs/design/accessibility-checklist.md).
 */
export function Alert({
  tone = "info",
  title,
  children,
  live = "off",
  actions,
  icon,
}: AlertProps) {
  const role = live === "off" ? undefined : live === "alert" ? "alert" : "status";
  return (
    <div className={`alert alert-${tone}`} role={role} aria-live={live === "off" ? undefined : "polite"}>
      <span className="alert-icon" aria-hidden="true">
        {icon ?? TONE_ICON[tone]}
      </span>
      <div className="alert-body">
        <p className="alert-title">{title}</p>
        {children && <div className="alert-text">{children}</div>}
        {actions && <div className="alert-actions">{actions}</div>}
      </div>
    </div>
  );
}
