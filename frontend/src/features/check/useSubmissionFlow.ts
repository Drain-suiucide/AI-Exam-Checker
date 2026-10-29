import { useCallback, useEffect, useRef, useState } from "react";
import type { CheckApi, CreateSubmissionInput } from "../../api/checkApi";
import { ApiError } from "../../api/client";
import type {
  Evaluation,
  ExamConfiguration,
  RequestReviewPayload,
  ReviewRequest,
  Submission,
  Transcription,
} from "../../api/types";

export type FlowStep =
  | "setup"
  | "preview"
  | "progress"
  | "transcription"
  | "result";

export type BusyKind =
  | "create"
  | "recognize"
  | "save"
  | "evaluate"
  | "result"
  | "review"
  | "transcription";

export interface FlowError {
  title: string;
  message: string;
  code: string | null;
  /** Ошибки полей из `VALIDATION_ERROR.details.fields`. */
  fields: Record<string, string>;
  retryable: boolean;
}

export interface FlowResultState {
  kind: "idle" | "loading" | "ready" | "empty" | "error";
  evaluation: Evaluation | null;
  emptyMessage: string | null;
}

type RetryAction =
  | { type: "configs" }
  | { type: "create"; input: CreateSubmissionInput; idempotencyKey: string }
  | { type: "recognize" }
  | { type: "transcription"; version: number }
  | { type: "save"; text: string; baseVersion: number }
  | { type: "evaluate"; transcriptionVersion: number }
  | { type: "result" }
  | { type: "review"; payload: RequestReviewPayload };

const EMPTY_FIELDS: Record<string, string> = {};

/** Переводит ошибку API в понятный пользователю текст (§1.3). */
export function describeError(error: unknown): FlowError {
  if (error instanceof ApiError) {
    const byCode: Record<string, { title: string; message?: string; retryable?: boolean }> = {
      NETWORK_ERROR: {
        title: "Нет связи с сервером",
        message:
          "Не удалось связаться с сервером. Проверьте подключение и повторите попытку.",
      },
      TIMEOUT: {
        title: "Сервер не ответил вовремя",
        message: "Обработка заняла слишком много времени. Повторите попытку.",
      },
      SERVICE_UNAVAILABLE: {
        title: "Сервис временно недоступен",
        message: "Сервер временно недоступен. Повторите попытку позже.",
      },
      RATE_LIMITED: {
        title: "Слишком много попыток",
        message:
          "Достигнут лимит попыток проверки. Подождите и попробуйте снова.",
        retryable: false,
      },
      DAILY_QUOTA_EXCEEDED: {
        title: "На сегодня лимит проверок исчерпан",
        message: "Попробуйте снова завтра или обратитесь к администратору.",
        retryable: false,
      },
      PAYLOAD_TOO_LARGE: {
        title: "Файл слишком большой",
        message: "Уменьшите размер файла и повторите загрузку.",
        retryable: false,
      },
      UNSUPPORTED_MEDIA_TYPE: {
        title: "Формат файла не поддерживается",
        message: "Поддерживаются изображения JPG, PNG и WebP.",
        retryable: false,
      },
      INVALID_IMAGE: {
        title: "Файл не удалось прочитать",
        message:
          "Изображение повреждено или не декодируется. Загрузите другой файл.",
        retryable: false,
      },
      VALIDATION_ERROR: {
        title: "Проверьте введённые данные",
        retryable: false,
      },
      INVALID_STATE: {
        title: "Действие сейчас недоступно",
        message:
          "Состояние отправки изменилось. Обновите данные и повторите действие.",
      },
      TRANSCRIPTION_VERSION_CONFLICT: {
        title: "Текст уже изменён",
        message:
          "Появилась более новая версия текста. Загрузите её и внесите правки заново.",
      },
      CONFIGURATION_NOT_APPROVED: {
        title: "Конфигурация не подтверждена",
        message:
          "В исследовательском прототипе доступны только подтверждённые конфигурации.",
        retryable: false,
      },
      EXAM_CONFIGURATION_NOT_FOUND: {
        title: "Конфигурация не найдена",
        message: "Выберите другую конфигурацию экзамена.",
        retryable: false,
      },
      FORBIDDEN: {
        title: "Действие запрещено",
        message: "Сервер отклонил запрос.",
        retryable: false,
      },
      RESULT_NOT_READY: {
        title: "Результат ещё не готов",
        message: "Дождитесь завершения оценивания и повторите попытку.",
      },
      NOT_FOUND: {
        title: "Данные не найдены",
        message:
          "Отправка или её данные недоступны. Возможно, срок хранения истёк.",
        retryable: false,
      },
    };

    const mapped = byCode[error.code];
    const fields: Record<string, string> = {};
    const details = error.details as
      | { fields?: { loc?: unknown[]; message?: string }[] }
      | null;
    if (details?.fields && Array.isArray(details.fields)) {
      for (const field of details.fields) {
        const key = Array.isArray(field.loc)
          ? String(field.loc[field.loc.length - 1])
          : "form";
        if (field.message) fields[key] = field.message;
      }
    }

    return {
      title: mapped?.title ?? "Не удалось выполнить действие",
      message: mapped?.message ?? error.message,
      code: error.code,
      fields,
      retryable: mapped?.retryable ?? true,
    };
  }

  if (error instanceof DOMException && error.name === "AbortError") {
    return {
      title: "Запрос отменён",
      message: "Запрос был отменён.",
      code: "ABORTED",
      fields: EMPTY_FIELDS,
      retryable: false,
    };
  }

  return {
    title: "Непредвиденная ошибка",
    message:
      error instanceof Error
        ? error.message
        : "Что-то пошло не так. Повторите попытку.",
    code: null,
    fields: EMPTY_FIELDS,
    retryable: true,
  };
}

function deriveStep(
  submission: Submission | null,
  override: "transcription" | null,
  manualEntry: boolean,
): FlowStep {
  if (!submission) return "setup";
  switch (submission.status) {
    case "recognizing":
    case "evaluating":
      return "progress";
    case "ready_for_recognition":
    case "recognition_failed":
      return override === "transcription" || manualEntry ? "transcription" : "preview";
    case "ready_for_evaluation":
    case "evaluation_failed":
      return "transcription";
    case "evaluated":
      return override === "transcription" ? "transcription" : "result";
    default:
      return "setup";
  }
}

function newIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `idem-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function submissionSignature(input: CreateSubmissionInput): string {
  return JSON.stringify({
    config: input.examConfigurationId,
    origin: input.dataOrigin,
    mode: input.inputMode,
    text: input.text ?? "",
    files: (input.files ?? []).map((file) => `${file.name}:${file.size}:${file.lastModified}`),
  });
}

export interface SubmissionFlow {
  configs: ExamConfiguration[];
  configsState: "loading" | "ready" | "error";
  configsError: FlowError | null;
  selectedConfig: ExamConfiguration | null;
  selectConfig: (id: string) => void;
  reloadConfigs: () => void;

  submission: Submission | null;
  token: string | null;
  step: FlowStep;
  busy: BusyKind | null;
  error: FlowError | null;
  pollError: FlowError | null;
  isSlow: boolean;
  manualEntry: boolean;

  transcription: Transcription | null;
  transcriptionState: "idle" | "loading" | "ready" | "error";
  transcriptionError: FlowError | null;

  resultState: FlowResultState;
  reviewRequest: ReviewRequest | null;
  reviewError: FlowError | null;

  createSubmission: (input: CreateSubmissionInput) => Promise<void>;
  recognize: () => Promise<void>;
  loadTranscription: (version?: number) => Promise<void>;
  saveTranscription: (text: string, baseVersion: number) => Promise<Transcription | null>;
  evaluate: (transcriptionVersion: number) => Promise<void>;
  loadResult: () => Promise<void>;
  requestReview: (payload: RequestReviewPayload) => Promise<boolean>;
  retry: () => void;
  reloadResult: () => void;
  dismissError: () => void;
  showTranscription: () => void;
  showResult: () => void;
  startManualEntry: () => void;
  startOver: () => Promise<void>;
  refreshSubmission: () => Promise<void>;
}

export function useSubmissionFlow(api: CheckApi | null): SubmissionFlow {
  const [configs, setConfigs] = useState<ExamConfiguration[]>([]);
  const [configsState, setConfigsState] = useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [configsError, setConfigsError] = useState<FlowError | null>(null);
  const [selectedConfigId, setSelectedConfigId] = useState<string | null>(null);

  const [submission, setSubmission] = useState<Submission | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [override, setOverride] = useState<"transcription" | null>(null);
  const [manualEntry, setManualEntry] = useState(false);
  const [busy, setBusy] = useState<BusyKind | null>(null);
  const [error, setError] = useState<FlowError | null>(null);
  const [pollError, setPollError] = useState<FlowError | null>(null);
  const [isSlow, setIsSlow] = useState(false);

  const [transcription, setTranscription] = useState<Transcription | null>(null);
  const [transcriptionState, setTranscriptionState] = useState<
    "idle" | "loading" | "ready" | "error"
  >("idle");
  const [transcriptionError, setTranscriptionError] = useState<FlowError | null>(null);

  const [resultState, setResultState] = useState<FlowResultState>({
    kind: "idle",
    evaluation: null,
    emptyMessage: null,
  });
  const [reviewRequest, setReviewRequest] = useState<ReviewRequest | null>(null);
  const [reviewError, setReviewError] = useState<FlowError | null>(null);

  const lastRetry = useRef<RetryAction | null>(null);
  const requestedTranscription = useRef<number | null>(null);
  const idempotency = useRef<{ signature: string; key: string } | null>(null);
  const resultRequested = useRef(false);
  const tokenRef = useRef<string | null>(null);

  tokenRef.current = token;

  const setRetry = useCallback((action: RetryAction) => {
    lastRetry.current = action;
  }, []);

  const fail = useCallback(
    (cause: unknown, retry: RetryAction | null): FlowError => {
      const described = describeError(cause);
      setError(described);
      if (retry && described.retryable) setRetry(retry);
      else lastRetry.current = null;
      return described;
    },
    [setRetry],
  );

  /* ----------------------------- configurations ---------------------------- */

  const loadConfigs = useCallback(async () => {
    if (!api) return;
    setConfigsState("loading");
    setConfigsError(null);
    lastRetry.current = { type: "configs" };
    try {
      const items = await api.listConfigurations("approved");
      setConfigs(items);
      setConfigsState("ready");
      setSelectedConfigId((current) => {
        if (current && items.some((item) => item.id === current)) return current;
        return items.find((item) => item.is_default)?.id ?? items[0]?.id ?? null;
      });
    } catch (cause) {
      setConfigsState("error");
      setConfigsError(describeError(cause));
    }
  }, [api]);

  useEffect(() => {
    if (!api) return;
    void loadConfigs();
  }, [api, loadConfigs]);

  /* ------------------------------- submission ------------------------------ */

  const applySubmission = useCallback((next: Submission) => {
    setSubmission(next);
    setPollError(null);
  }, []);

  const loadTranscription = useCallback(
    async (version?: number) => {
      const current = submission;
      const currentToken = tokenRef.current;
      if (!api || !current || !currentToken) return;
      const targetVersion = version ?? current.current_transcription?.version;
      setTranscriptionState("loading");
      setTranscriptionError(null);
      lastRetry.current = targetVersion
        ? { type: "transcription", version: targetVersion }
        : { type: "transcription", version: 0 };
      try {
        const data = await api.getTranscription(current.id, currentToken, version);
        setTranscription(data);
        setTranscriptionState("ready");
        requestedTranscription.current = data.version;
      } catch (cause) {
        setTranscriptionState("error");
        setTranscriptionError(describeError(cause));
      }
    },
    [api, submission],
  );

  const createSubmission = useCallback(
    async (input: CreateSubmissionInput) => {
      if (!api) return;
      setBusy("create");
      setError(null);
      const signature = submissionSignature(input);
      if (!idempotency.current || idempotency.current.signature !== signature) {
        idempotency.current = { signature, key: newIdempotencyKey() };
      }
      const key = idempotency.current.key;
      lastRetry.current = { type: "create", input, idempotencyKey: key };
      try {
        const created = await api.createSubmission(input, key);
        const { access_token: accessToken, ...rest } = created;
        setToken(accessToken);
        tokenRef.current = accessToken;
        setSubmission(rest);
        setOverride(null);
        setManualEntry(false);
        setTranscription(null);
        setTranscriptionState("idle");
        requestedTranscription.current = null;
        setResultState({ kind: "idle", evaluation: null, emptyMessage: null });
        resultRequested.current = false;
        setReviewRequest(null);
        idempotency.current = null;
        lastRetry.current = null;
      } catch (cause) {
        fail(cause, { type: "create", input, idempotencyKey: key });
      } finally {
        setBusy(null);
      }
    },
    [api, fail],
  );

  const refreshSubmission = useCallback(async () => {
    const current = submission;
    const currentToken = tokenRef.current;
    if (!api || !current || !currentToken) return;
    try {
      const next = await api.getSubmission(current.id, currentToken);
      applySubmission(next);
    } catch (cause) {
      setPollError(describeError(cause));
    }
  }, [api, submission, applySubmission]);

  const recognize = useCallback(async () => {
    const current = submission;
    const currentToken = tokenRef.current;
    if (!api || !current || !currentToken) return;
    setBusy("recognize");
    setError(null);
    setManualEntry(false);
    lastRetry.current = { type: "recognize" };
    try {
      const next = await api.recognize(current.id, currentToken, current.status === "recognition_failed");
      applySubmission(next);
    } catch (cause) {
      fail(cause, { type: "recognize" });
    } finally {
      setBusy(null);
    }
  }, [api, submission, applySubmission, fail]);

  const evaluate = useCallback(
    async (transcriptionVersion: number) => {
      const current = submission;
      const currentToken = tokenRef.current;
      if (!api || !current || !currentToken) return;
      setBusy("evaluate");
      setError(null);
      setOverride(null);
      setResultState({ kind: "idle", evaluation: null, emptyMessage: null });
      resultRequested.current = false;
      lastRetry.current = { type: "evaluate", transcriptionVersion };
      try {
        const next = await api.evaluate(current.id, currentToken, transcriptionVersion);
        applySubmission(next);
      } catch (cause) {
        fail(cause, { type: "evaluate", transcriptionVersion });
      } finally {
        setBusy(null);
      }
    },
    [api, submission, applySubmission, fail],
  );

  const saveTranscription = useCallback(
    async (text: string, baseVersion: number): Promise<Transcription | null> => {
      const current = submission;
      const currentToken = tokenRef.current;
      if (!api || !current || !currentToken) return null;
      setBusy("save");
      setError(null);
      lastRetry.current = { type: "save", text, baseVersion };
      try {
        const data = await api.updateTranscription(current.id, currentToken, baseVersion, text);
        setTranscription(data);
        setTranscriptionState("ready");
        requestedTranscription.current = data.version;
        setManualEntry(false);
        setSubmission((prev) =>
          prev
            ? {
                ...prev,
                status: "ready_for_evaluation",
                current_transcription: {
                  id: data.id,
                  version: data.version,
                  source: data.source,
                  char_count: data.char_count,
                  text_sha256: data.text_sha256,
                  created_at: data.created_at,
                },
                allowed_actions: ["edit_transcription", "evaluate", "delete"],
                poll_interval_ms: null,
              }
            : prev,
        );
        lastRetry.current = null;
        return data;
      } catch (cause) {
        fail(cause, { type: "save", text, baseVersion });
        return null;
      } finally {
        setBusy(null);
      }
    },
    [api, submission, fail],
  );

  const loadResult = useCallback(async () => {
    const current = submission;
    const currentToken = tokenRef.current;
    if (!api || !current || !currentToken) return;
    if (resultRequested.current) return;
    resultRequested.current = true;
    setBusy("result");
    setError(null);
    setResultState({ kind: "loading", evaluation: null, emptyMessage: null });
    lastRetry.current = { type: "result" };
    try {
      const evaluation = await api.getResult(current.id, currentToken);
      setResultState({ kind: "ready", evaluation, emptyMessage: null });
      setReviewRequest(evaluation.expert_review ?? null);
      lastRetry.current = null;
    } catch (cause) {
      const described = describeError(cause);
      if (described.code === "RESULT_NOT_READY") {
        setResultState({
          kind: "empty",
          evaluation: null,
          emptyMessage: described.message,
        });
      } else {
        setResultState({ kind: "error", evaluation: null, emptyMessage: null });
        fail(cause, { type: "result" });
      }
    } finally {
      setBusy(null);
    }
  }, [api, submission, fail]);

  const requestReview = useCallback(
    async (payload: RequestReviewPayload): Promise<boolean> => {
      const current = submission;
      const currentToken = tokenRef.current;
      if (!api || !current || !currentToken) return false;
      setBusy("review");
      setReviewError(null);
      lastRetry.current = { type: "review", payload };
      try {
        const review = await api.requestReview(current.id, currentToken, payload);
        setReviewRequest(review);
        setSubmission((prev) =>
          prev
            ? {
                ...prev,
                review_request: {
                  id: review.id,
                  status: review.status,
                  created_at: review.created_at,
                },
              }
            : prev,
        );
        lastRetry.current = null;
        return true;
      } catch (cause) {
        setReviewError(describeError(cause));
        return false;
      } finally {
        setBusy(null);
      }
    },
    [api, submission],
  );

  /* -------------------------------- polling -------------------------------- */

  const pollStatus = submission?.status;
  const pollUpdatedAt = submission?.updated_at;
  const pollInterval = submission?.poll_interval_ms ?? 2000;
  const processing = pollStatus === "recognizing" || pollStatus === "evaluating";

  useEffect(() => {
    if (!api || !submission || !tokenRef.current) return;
    if (!processing) return;
    let cancelled = false;
    const timer = setTimeout(async () => {
      try {
        const next = await api.getSubmission(submission.id, tokenRef.current as string);
        if (!cancelled) applySubmission(next);
      } catch (cause) {
        if (!cancelled) setPollError(describeError(cause));
      }
    }, pollInterval);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
    // pollUpdatedAt перезапускает опрос после каждого ответа сервера.
  }, [api, submission, processing, pollInterval, pollUpdatedAt, applySubmission]);

  useEffect(() => {
    if (!processing) {
      setIsSlow(false);
      return;
    }
    setIsSlow(false);
    const timer = setTimeout(() => setIsSlow(true), 15000);
    return () => clearTimeout(timer);
  }, [processing]);

  /* --------------------------- auto load effects ---------------------------- */

  const derivedStep = deriveStep(submission, override, manualEntry);

  useEffect(() => {
    if (!api || !submission || derivedStep !== "transcription") return;
    const summary = submission.current_transcription;
    if (!summary) return;
    if (requestedTranscription.current === summary.version) return;
    if (transcription?.version === summary.version) {
      requestedTranscription.current = summary.version;
      return;
    }
    requestedTranscription.current = summary.version;
    void loadTranscription(summary.version);
  }, [api, submission, derivedStep, transcription?.version, loadTranscription]);

  useEffect(() => {
    if (!api || !submission) return;
    if (submission.status !== "evaluated") return;
    if (resultState.kind !== "idle") return;
    if (resultRequested.current) return;
    void loadResult();
  }, [api, submission, resultState.kind, loadResult]);

  /* --------------------------------- actions -------------------------------- */

  const retry = useCallback(() => {
    const action = lastRetry.current;
    setError(null);
    if (!action) return;
    switch (action.type) {
      case "configs":
        void loadConfigs();
        break;
      case "create":
        void createSubmission(action.input);
        break;
      case "recognize":
        void recognize();
        break;
      case "transcription":
        requestedTranscription.current = null;
        void loadTranscription(action.version || undefined);
        break;
      case "save":
        void saveTranscription(action.text, action.baseVersion);
        break;
      case "evaluate":
        void evaluate(action.transcriptionVersion);
        break;
      case "result":
        resultRequested.current = false;
        void loadResult();
        break;
      case "review":
        void requestReview(action.payload);
        break;
    }
  }, [
    loadConfigs,
    createSubmission,
    recognize,
    loadTranscription,
    saveTranscription,
    evaluate,
    loadResult,
    requestReview,
  ]);

  const startOver = useCallback(async () => {
    const current = submission;
    const currentToken = tokenRef.current;
    if (api && current && currentToken) {
      try {
        await api.deleteSubmission(current.id, currentToken);
      } catch {
        // Удаление — право пользователя, а не обязательный шаг сценария.
      }
    }
    setSubmission(null);
    setToken(null);
    tokenRef.current = null;
    setOverride(null);
    setManualEntry(false);
    setTranscription(null);
    setTranscriptionState("idle");
    requestedTranscription.current = null;
    setResultState({ kind: "idle", evaluation: null, emptyMessage: null });
    resultRequested.current = false;
    setReviewRequest(null);
    setReviewError(null);
    setError(null);
    setPollError(null);
    idempotency.current = null;
    lastRetry.current = null;
  }, [api, submission]);

  useEffect(() => {
    if (!submission) {
      requestedTranscription.current = null;
      resultRequested.current = false;
    }
  }, [submission]);

  const selectConfig = useCallback((id: string) => {
    setSelectedConfigId(id);
    setError(null);
  }, []);

  const selectedConfig =
    configs.find((item) => item.id === selectedConfigId) ?? null;

  return {
    configs,
    configsState,
    configsError,
    selectedConfig,
    selectConfig,
    reloadConfigs: () => void loadConfigs(),

    submission,
    token,
    step: derivedStep,
    busy,
    error,
    pollError,
    isSlow,
    manualEntry,

    transcription,
    transcriptionState,
    transcriptionError,

    resultState,
    reviewRequest,
    reviewError,

    createSubmission,
    recognize,
    loadTranscription,
    saveTranscription,
    evaluate,
    loadResult,
    requestReview,
    retry,
    reloadResult: () => {
      resultRequested.current = false;
      setResultState({ kind: "idle", evaluation: null, emptyMessage: null });
      void loadResult();
    },
    dismissError: () => {
      setError(null);
      lastRetry.current = null;
    },
    showTranscription: () => setOverride("transcription"),
    showResult: () => setOverride(null),
    startManualEntry: () => {
      setManualEntry(true);
      setOverride("transcription");
      setError(null);
    },
    startOver,
    refreshSubmission,
  };
}
