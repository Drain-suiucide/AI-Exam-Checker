/**
 * Тестовый двойник backend: реализует маршруты API_CONTRACT на уровне fetch.
 * Используется только тестами; в production-код не попадает.
 */
import { vi } from "vitest";
import type {
  Evaluation,
  ExamConfiguration,
  ReviewRequest,
  Submission,
  SubmissionCreated,
  Transcription,
} from "../api/types";

const CONFIG: ExamConfiguration = {
  id: "11111111-1111-4111-8111-111111111111",
  slug: "ege-history-demo",
  status: "approved",
  is_default: true,
  exam: {
    code: "ege-history",
    subject: "history",
    title: "ЕГЭ по истории",
    version_label: "demo",
    exam_year: 2026,
  },
  task: {
    task_version_id: "22222222-2222-4222-8222-222222222222",
    task_key: "history-concept-and-fact",
    task_number: "19",
    version: 1,
    title: "Историческое понятие и факт",
    statement: "Раскройте смысл понятия и приведите один исторический факт.",
    materials: [],
    max_score: 2,
  },
  criteria_version: {
    id: "33333333-3333-4333-8333-333333333333",
    version: 1,
    aggregation: { type: "sum" },
    max_score_total: 2,
    criteria: [
      {
        id: "44444444-4444-4444-8444-444444444444",
        code: "K1",
        position: 1,
        title: "Смысл понятия",
        description: "Понятие раскрыто.",
        max_score: 1,
        levels: [],
      },
      {
        id: "55555555-5555-4555-8555-555555555555",
        code: "K2",
        position: 2,
        title: "Конкретный факт",
        description: "Приведён конкретный факт.",
        max_score: 1,
        levels: [],
      },
    ],
  },
  evaluation_profile: {
    id: "66666666-6666-4666-8666-666666666666",
    code: "demo-history-v1",
    version: 1,
    model_provider: "mock",
    model_name: "demo",
  },
  sources: [],
  limits: {
    max_files: 4,
    max_file_bytes: 8 * 1024 * 1024,
    allowed_mime_types: ["image/jpeg", "image/png", "image/webp"],
    min_answer_chars: 10,
    max_answer_chars: 10000,
  },
  created_at: "2026-10-01T00:00:00Z",
  approved_at: "2026-10-01T00:00:00Z",
};

const OCR_TEXT = "Понятие раскрыто в демонстрационном ответе, факт приведён условно.";

interface FakeState {
  submission: Submission | null;
  token: string | null;
  text: string | null;
  transcriptionVersion: number;
  evaluation: Evaluation | null;
  review: ReviewRequest | null;
  pollsWhileProcessing: number;
}

export interface FakeBackend {
  calls: { method: string; path: string }[];
  state: FakeState;
  setConfigs: (items: ExamConfiguration[]) => void;
  failNext: (method: string, pathPart: string, response: { status: number; code: string; message: string }) => void;
  setResultNotReady: (value: boolean) => void;
  completeProcessing: () => void;
  restore: () => void;
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", "X-Request-ID": "test-request" },
  });
}

function errorResponse(status: number, code: string, message: string, details: unknown = null) {
  return json({ error: { code, message, details, request_id: "test-request" } }, status);
}

function makeEvaluation(submission: Submission, text: string): Evaluation {
  const quote = text.slice(0, Math.min(40, text.length));
  return {
    id: "77777777-7777-4777-8777-777777777777",
    submission_id: submission.id,
    status: "succeeded",
    transcription_id: "88888888-8888-4888-8888-888888888888",
    transcription_version: 1,
    is_current: true,
    versions: {
      exam_configuration_id: CONFIG.id,
      exam_configuration_status: "approved",
      exam: { code: "ege-history", version_label: "demo", exam_year: 2026 },
      task_version: {
        id: CONFIG.task.task_version_id,
        task_key: CONFIG.task.task_key,
        task_number: "19",
        version: 1,
        content_sha256: "a".repeat(64),
      },
      criteria_version: { id: CONFIG.criteria_version.id, version: 1, content_sha256: "b".repeat(64) },
      evaluation_profile: {
        id: CONFIG.evaluation_profile.id,
        code: "demo-history-v1",
        version: 1,
        prompt_sha256: "c".repeat(64),
      },
      model: { provider: "mock", requested: "demo", reported: "demo" },
      source_editions: [],
    },
    total_score: 1,
    max_score: 2,
    overall_confidence: 0.42,
    needs_review: true,
    flags: ["LOW_CONFIDENCE"],
    summary: "Ответ раскрывает понятие частично.",
    criteria: [
      {
        criterion_id: CONFIG.criteria_version.criteria[0].id,
        code: "K1",
        title: "Смысл понятия",
        position: 1,
        score: 1,
        max_score: 1,
        confidence: 0.82,
        rationale: "Понятие раскрыто корректно.",
        uncertainty_note: null,
        flags: [],
        evidence: [
          {
            id: "99999999-9999-4999-8999-999999999991",
            kind: "supports",
            char_start: 0,
            char_end: quote.length,
            quote,
            note: null,
          },
        ],
      },
      {
        criterion_id: CONFIG.criteria_version.criteria[1].id,
        code: "K2",
        title: "Конкретный факт",
        position: 2,
        score: 0,
        max_score: 1,
        confidence: 0.31,
        rationale: "Конкретный факт не подтверждён.",
        uncertainty_note: "Факт сформулирован неполно.",
        flags: ["LOW_CONFIDENCE", "AMBIGUOUS"],
        evidence: [],
      },
    ],
    final: { total_score: 1, max_score: 2, source: "model" },
    expert_review: null,
    disclaimer: "Ориентировочная оценка модели. Не является официальным баллом ЕГЭ.",
    created_at: "2026-10-01T00:00:00Z",
  };
}

export function installFakeBackend(): FakeBackend {
  let configs: ExamConfiguration[] = [CONFIG];
  const failures: { method: string; pathPart: string; response: { status: number; code: string; message: string } }[] = [];
  let resultNotReady = false;

  const backend: FakeBackend = {
    calls: [],
    state: {
      submission: null,
      token: null,
      text: null,
      transcriptionVersion: 0,
      evaluation: null,
      review: null,
      pollsWhileProcessing: 0,
    },
    setConfigs(items) {
      configs = items;
    },
    failNext(method, pathPart, response) {
      failures.push({ method, pathPart, response });
    },
    setResultNotReady(value) {
      resultNotReady = value;
    },
    completeProcessing() {
      const s = backend.state.submission;
      if (!s) return;
      if (s.status === "recognizing") {
        backend.state.text = OCR_TEXT;
        backend.state.transcriptionVersion = 1;
        backend.state.submission = {
          ...s,
          status: "ready_for_evaluation",
          poll_interval_ms: null,
          current_transcription: {
            id: "88888888-8888-4888-8888-888888888888",
            version: 1,
            source: "ocr",
            char_count: OCR_TEXT.length,
            text_sha256: "d".repeat(64),
            created_at: "2026-10-01T00:00:10Z",
          },
          recognition: s.recognition
            ? { ...s.recognition, status: "succeeded", finished_at: "2026-10-01T00:00:10Z" }
            : null,
          allowed_actions: ["edit_transcription", "evaluate", "delete", "recognize"],
        };
      } else if (s.status === "evaluating") {
        const evaluation = makeEvaluation(s, backend.state.text ?? "");
        backend.state.evaluation = evaluation;
        backend.state.submission = {
          ...s,
          status: "evaluated",
          poll_interval_ms: null,
          evaluation: {
            id: evaluation.id,
            attempt_no: 1,
            status: "succeeded",
            transcription_version: backend.state.transcriptionVersion,
            is_current: true,
            started_at: "2026-10-01T00:00:10Z",
            finished_at: "2026-10-01T00:00:20Z",
            error: null,
            total_score: 1,
            max_score: 2,
          },
          allowed_actions: ["edit_transcription", "view_result", "request_review", "delete"],
        };
      }
    },
    restore() {
      vi.unstubAllGlobals();
    },
  };

  function submissionFor(input: { mode: string; text?: string | null; configId: string }): Submission {
    const isText = input.mode === "text";
    return {
      id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
      status: isText ? "ready_for_evaluation" : "ready_for_recognition",
      input_mode: isText ? "text" : "image",
      data_origin: "synthetic",
      exam_configuration_id: input.configId,
      exam_configuration_status: "approved",
      created_at: "2026-10-01T00:00:00Z",
      updated_at: "2026-10-01T00:00:00Z",
      expires_at: null,
      files: isText
        ? []
        : [
            {
              id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
              page_index: 0,
              mime_type: "image/png",
              size_bytes: 2048,
              width_px: 800,
              height_px: 1200,
              sha256: "e".repeat(64),
            },
          ],
      current_transcription: isText
        ? {
            id: "88888888-8888-4888-8888-888888888888",
            version: 1,
            source: "manual_input",
            char_count: (input.text ?? "").length,
            text_sha256: "f".repeat(64),
            created_at: "2026-10-01T00:00:00Z",
          }
        : null,
      recognition: null,
      evaluation: null,
      review_request: null,
      allowed_actions: isText
        ? ["edit_transcription", "evaluate", "delete"]
        : ["recognize", "edit_transcription", "delete"],
      poll_interval_ms: null,
    };
  }

  const handler = vi.fn(async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    const parsed = new URL(url, "http://localhost");
    const path = parsed.pathname;
    const query = parsed.searchParams;
    const method = (init?.method ?? "GET").toUpperCase();
    backend.calls.push({ method, path });

    const failureIndex = failures.findIndex(
      (failure) => failure.method === method && path.includes(failure.pathPart),
    );
    if (failureIndex >= 0) {
      const [failure] = failures.splice(failureIndex, 1);
      return errorResponse(failure.response.status, failure.response.code, failure.response.message);
    }

    // GET /exam-configurations
    if (method === "GET" && path === "/api/v1/exam-configurations") {
      const status = query.get("status") ?? "approved";
      const items = status === "approved" ? configs : configs.filter((item) => item.status === status);
      return json({ items });
    }

    // POST /submissions
    if (method === "POST" && path === "/api/v1/submissions") {
      const form = init?.body as FormData;
      const mode = String(form.get("input_mode"));
      const configId = String(form.get("exam_configuration_id"));
      const text = form.get("text") === null ? null : String(form.get("text"));
      const submission = submissionFor({ mode, text, configId });
      backend.state.submission = submission;
      backend.state.text = text;
      backend.state.transcriptionVersion = mode === "text" ? 1 : 0;
      backend.state.evaluation = null;
      backend.state.review = null;
      backend.state.pollsWhileProcessing = 0;
      backend.state.token = "sbt_test_token";
      const created: SubmissionCreated = { ...submission, access_token: "sbt_test_token" };
      return json(created, 201);
    }

    const submissionMatch = path.match(/^\/api\/v1\/submissions\/([^/]+)(\/.*)?$/);
    if (submissionMatch) {
      const rest = submissionMatch[2] ?? "";
      const current = backend.state.submission;
      if (!current) return errorResponse(404, "NOT_FOUND", "Отправка не найдена.");

      if (rest === "" && method === "GET") {
        if (current.status === "recognizing" || current.status === "evaluating") {
          backend.state.pollsWhileProcessing += 1;
          if (backend.state.pollsWhileProcessing >= 2) backend.completeProcessing();
        }
        return json(backend.state.submission);
      }
      if (rest === "" && method === "DELETE") {
        backend.state.submission = null;
        return new Response(null, { status: 204 });
      }
      if (rest === "/recognize" && method === "POST") {
        backend.state.submission = {
          ...current,
          status: "recognizing",
          poll_interval_ms: 10,
          recognition: {
            id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
            attempt_no: 1,
            status: "running",
            engine: "mock",
            engine_version: "1",
            started_at: "2026-10-01T00:00:00Z",
            finished_at: null,
            error: null,
            transcription_id: null,
          },
          allowed_actions: [],
        };
        backend.state.pollsWhileProcessing = 0;
        return json(backend.state.submission, 202);
      }
      if (rest === "/transcription" && method === "GET") {
        if (backend.state.text === null) {
          return errorResponse(404, "NOT_FOUND", "Текст ещё не распознан.");
        }
        const transcription: Transcription = {
          id: "88888888-8888-4888-8888-888888888888",
          version: backend.state.transcriptionVersion,
          source: current.input_mode === "text" ? "manual_input" : "user_edit",
          char_count: backend.state.text.length,
          text_sha256: "d".repeat(64),
          created_at: "2026-10-01T00:00:10Z",
          text: backend.state.text,
          parent_version: null,
          ocr: null,
        };
        return json(transcription);
      }
      if (rest === "/transcription" && method === "PATCH") {
        const body = JSON.parse(String(init?.body)) as { base_version: number; text: string };
        if (body.base_version !== backend.state.transcriptionVersion) {
          return errorResponse(409, "TRANSCRIPTION_VERSION_CONFLICT", "Конфликт версий.", {
            current_version: backend.state.transcriptionVersion,
          });
        }
        const changed = body.text !== backend.state.text;
        if (changed) backend.state.transcriptionVersion += 1;
        backend.state.text = body.text;
        backend.state.submission = {
          ...current,
          status: "ready_for_evaluation",
          evaluation: null,
          current_transcription: {
            id: "88888888-8888-4888-8888-888888888888",
            version: backend.state.transcriptionVersion,
            source: "user_edit",
            char_count: body.text.length,
            text_sha256: "d".repeat(64),
            created_at: "2026-10-01T00:00:15Z",
          },
          allowed_actions: ["edit_transcription", "evaluate", "delete", "recognize"],
        };
        return json({
          id: "88888888-8888-4888-8888-888888888888",
          version: backend.state.transcriptionVersion,
          source: "user_edit",
          char_count: body.text.length,
          text_sha256: "d".repeat(64),
          created_at: "2026-10-01T00:00:15Z",
          text: body.text,
          parent_version: body.base_version,
          ocr: null,
        } satisfies Transcription);
      }
      if (rest === "/evaluate" && method === "POST") {
        backend.state.submission = {
          ...current,
          status: "evaluating",
          poll_interval_ms: 10,
          evaluation: {
            id: "77777777-7777-4777-8777-777777777777",
            attempt_no: 1,
            status: "running",
            transcription_version: backend.state.transcriptionVersion,
            is_current: true,
            started_at: "2026-10-01T00:00:20Z",
            finished_at: null,
            error: null,
            total_score: null,
            max_score: null,
          },
          allowed_actions: [],
        };
        backend.state.pollsWhileProcessing = 0;
        return json(backend.state.submission, 202);
      }
      if (rest === "/result" && method === "GET") {
        if (resultNotReady || !backend.state.evaluation) {
          return errorResponse(409, "RESULT_NOT_READY", "Результат ещё не готов.", {
            submission_status: current.status,
          });
        }
        return json(backend.state.evaluation);
      }
      if (rest === "/review-requests" && method === "POST") {
        const body = JSON.parse(String(init?.body)) as {
          evaluation_id: string;
          reason_code: ReviewRequest["reason_code"];
          criterion_codes: string[];
          comment: string | null;
        };
        backend.state.review = {
          id: "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
          submission_id: current.id,
          evaluation_id: body.evaluation_id,
          status: "open",
          reason_code: body.reason_code,
          criterion_codes: body.criterion_codes,
          comment: body.comment,
          created_at: "2026-10-01T00:01:00Z",
          resolved_at: null,
          decision: null,
        };
        backend.state.submission = {
          ...current,
          review_request: {
            id: backend.state.review.id,
            status: "open",
            created_at: backend.state.review.created_at,
          },
        };
        return json(backend.state.review, 201);
      }
      return errorResponse(404, "NOT_FOUND", "Маршрут не найден.");
    }

    return errorResponse(404, "NOT_FOUND", "Маршрут не найден.");
  });

  vi.stubGlobal("fetch", handler);
  return backend;
}

export { CONFIG as FAKE_CONFIG, OCR_TEXT as FAKE_OCR_TEXT };
