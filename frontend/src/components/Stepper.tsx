import { COMPACT_STEPPER_QUERY, useMediaQuery } from "../hooks/useMediaQuery";

export interface StepDefinition {
  key: string;
  label: string;
}

interface StepperProps {
  steps: StepDefinition[];
  /** Индекс текущего шага, с 0. */
  current: number;
  completed: number;
}

/**
 * Индикатор шагов сценария. На узких экранах сворачивается в компактный
 * текст «Шаг 2 из 5: …», чтобы не ломать вёрстку.
 */
export function Stepper({ steps, current, completed }: StepperProps) {
  const compact = useMediaQuery(COMPACT_STEPPER_QUERY);
  const safeCurrent = Math.min(Math.max(current, 0), steps.length - 1);
  const active = steps[safeCurrent];

  return (
    <>
      <p className="visually-hidden" aria-live="polite">
        Шаг {safeCurrent + 1} из {steps.length}: {active?.label}
      </p>
      <nav className="stepper" aria-label="Этапы проверки">
      {compact ? (
        <ol className="stepper-compact">
          <li className="stepper-count">
            Шаг {safeCurrent + 1} из {steps.length}
          </li>
          <li className="stepper-active">{active?.label}</li>
        </ol>
      ) : (
        <ol className="stepper-list">
          {steps.map((step, index) => {
            const state =
              index < completed || index < safeCurrent
                ? "complete"
                : index === safeCurrent
                  ? "current"
                  : "pending";
            return (
              <li
                key={step.key}
                className={`stepper-item stepper-${state}`}
                aria-current={index === safeCurrent ? "step" : undefined}
              >
                <span className="stepper-marker" aria-hidden="true">
                  {state === "complete" ? "✓" : index + 1}
                </span>
                <span className="stepper-label">
                  {step.label}
                  <span className="visually-hidden">
                    {state === "complete"
                      ? " — завершён"
                      : state === "current"
                        ? " — текущий шаг"
                        : " — не начат"}
                  </span>
                </span>
              </li>
            );
          })}
        </ol>
      )}
      </nav>
    </>
  );
}
