/**
 * HTTP-клиент API v1 (API_CONTRACT §1.2, §1.4).
 *
 * - Все ответы с данными пользователя не кэшируются (Cache-Control ставит сервер,
 *   клиент дополнительно просит `cache: "no-store"`).
 * - Ошибки нормализуются в `ApiError`: `code` стабилен, `message` — для человека.
 * - Ничего не сохраняется в localStorage/sessionStorage.
 */

export const API_BASE = "/api/v1";

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details: unknown;
  readonly requestId: string | null;

  constructor(init: {
    code: string;
    message: string;
    status: number;
    details?: unknown;
    requestId?: string | null;
  }) {
    super(init.message);
    this.name = "ApiError";
    this.code = init.code;
    this.status = init.status;
    this.details = init.details ?? null;
    this.requestId = init.requestId ?? null;
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

interface ErrorEnvelope {
  error?: { code?: unknown; message?: unknown; details?: unknown; request_id?: unknown };
  detail?: unknown;
}

function newRequestId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `req-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

/** Разбирает тело ошибки: формат контракта `{error: {...}}` или FastAPI `{detail}`. */
async function parseErrorResponse(response: Response): Promise<ApiError> {
  let envelope: ErrorEnvelope | null = null;
  try {
    envelope = (await response.json()) as ErrorEnvelope;
  } catch {
    envelope = null;
  }

  const error = envelope?.error;
  let code = `HTTP_${response.status}`;
  let message = "Запрос завершился ошибкой.";
  let details: unknown = null;
  let requestId: string | null = response.headers.get("X-Request-ID");

  if (error && typeof error.code === "string") {
    code = error.code;
    if (typeof error.message === "string") message = error.message;
    details = error.details ?? null;
    if (typeof error.request_id === "string") requestId = error.request_id;
  } else if (typeof envelope?.detail === "string") {
    // FastAPI HTTPException вне конверта API_CONTRACT.
    message = envelope.detail;
  }

  if (code === "HTTP_404" && response.url?.includes("/submissions/")) {
    // Пока submissions не реализован в backend, сервер отвечает стандартным 404.
    message = "Маршрут API недоступен. Возможно, backend ещё не поддерживает проверку ответов.";
  }

  return new ApiError({ code, message, status: response.status, details, requestId });
}

export interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  headers?: Record<string, string>;
  body?: BodyInit;
  signal?: AbortSignal;
  /** По умолчанию 30 с; для GET — 5 с (API_CONTRACT §1.6). */
  timeoutMs?: number;
}

function withTimeout(signal: AbortSignal | undefined, timeoutMs: number) {
  const controller = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);

  const onAbort = () => controller.abort();
  if (signal) {
    if (signal.aborted) controller.abort();
    else signal.addEventListener("abort", onAbort, { once: true });
  }

  return {
    signal: controller.signal,
    isTimedOut: () => timedOut,
    cleanup: () => {
      clearTimeout(timer);
      signal?.removeEventListener("abort", onAbort);
    },
  };
}

/** Выполняет запрос и возвращает JSON. Для 204 возвращает `undefined`. */
export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const method = options.method ?? "GET";
  const timeoutMs = options.timeoutMs ?? (method === "GET" ? 5000 : 30000);
  const timeout = withTimeout(options.signal, timeoutMs);

  const headers: Record<string, string> = {
    Accept: "application/json",
    "X-Request-ID": newRequestId(),
    ...options.headers,
  };

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: options.body,
      signal: timeout.signal,
      cache: "no-store",
      credentials: "same-origin",
    });

    if (!response.ok) {
      throw await parseErrorResponse(response);
    }
    if (response.status === 204) {
      return undefined as T;
    }
    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (timeout.isTimedOut()) {
      throw new ApiError({
        code: "TIMEOUT",
        message: "Сервер не ответил вовремя. Повторите попытку.",
        status: 0,
      });
    }
    if (options.signal?.aborted) {
      throw error;
    }
    throw new ApiError({
      code: "NETWORK_ERROR",
      message:
        "Не удалось связаться с сервером. Проверьте подключение и повторите попытку.",
      status: 0,
    });
  } finally {
    timeout.cleanup();
  }
}
