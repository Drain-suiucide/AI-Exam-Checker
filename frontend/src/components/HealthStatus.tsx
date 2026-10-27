import { useEffect, useState } from "react";
import { fetchHealth } from "../api/health";

type HealthState =
  | { kind: "loading" }
  | { kind: "ok"; service: string; version: string }
  | { kind: "error"; message: string };

const LABELS: Record<HealthState["kind"], string> = {
  loading: "Проверяем состояние backend…",
  ok: "Backend доступен",
  error: "Backend недоступен",
};

/**
 * Статус backend по GET /api/v1/health.
 * В dev — через прокси Vite, в compose — через прокси nginx.
 */
export function HealthStatus() {
  const [state, setState] = useState<HealthState>({ kind: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    fetchHealth(controller.signal)
      .then((data) =>
        setState({ kind: "ok", service: data.service, version: data.version }),
      )
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        const message =
          error instanceof Error ? error.message : "Неизвестная ошибка сети.";
        setState({ kind: "error", message });
      });
    return () => controller.abort();
  }, []);

  return (
    <section className="card" aria-live="polite">
      <h2 className="card-title">Состояние сервисов</h2>
      <span className={`status-badge status-badge-${state.kind}`}>
        {LABELS[state.kind]}
      </span>
      {state.kind === "ok" && (
        <p className="card-text">
          {state.service}, версия {state.version}. Ответ получен по
          {" "}
          <code>/api/v1/health</code>.
        </p>
      )}
      {state.kind === "error" && (
        <p className="card-text">
          {state.message}. Убедитесь, что backend запущен (см.
          docs/deployment/local-development.md), и обновите страницу.
        </p>
      )}
      {state.kind === "loading" && (
        <p className="card-text">Запрос состояния backend выполняется…</p>
      )}
    </section>
  );
}
