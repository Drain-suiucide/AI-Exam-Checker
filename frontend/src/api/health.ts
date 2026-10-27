/** Ответ GET /api/v1/health (API_CONTRACT §1.1). */
export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

/** Запрос health-check backend. Ошибки сети возвращаются вызывающему коду. */
export async function fetchHealth(
  signal?: AbortSignal,
): Promise<HealthResponse> {
  const response = await fetch("/api/v1/health", { signal });
  if (!response.ok) {
    throw new Error(`Backend ответил со статусом ${response.status}`);
  }
  return (await response.json()) as HealthResponse;
}
