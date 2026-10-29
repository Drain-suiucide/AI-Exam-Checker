/**
 * Демонстрационная реализация CheckApi.
 *
 * Включается ТОЛЬКО через `resolveDemoMode` (dev + VITE_DEMO_MODE=true).
 * Содержимое ниже — синтетическое: никаких реальных работ, критериев ФИПИ или
 * балов ЕГЭ. В интерфейсе демо-режим всегда помечен явным баннером.
 */
import { ApiError } from "../api/client";
import type { CheckApi, CreateSubmissionInput } from "../api/checkApi";
import type {
  CriterionResult,
  Evaluation,
  ExamConfiguration,
  RequestReviewPayload,
  ReviewRequest,
  Submission,
  SubmissionCreated,
  Transcription,
  UUID,
} from "../api/types";

const CONFIG: ExamConfiguration = {
  id: "demo-config-0001",
  slug: "ege-history-demo",
  status: "approved",
  is_default: true,
  exam: {
    code: "ege-history",
    subject: "history",
    title: "ЕГЭ по истории (демо)",
    version_label: "demo",
    exam_year: 2026,
  },
  task: {
    task_version_id: "demo-task-0001",
    task_key: "history-concept-and-fact",
    task_number: "19",
    version: 1,
    title: "Историческое понятие и факт (демо)",
    statement:
      "Демонстрационное условие: раскройте смысл исторического понятия и приведите один конкретный исторический факт.",
    materials: [],
    max_score: 2,
  },
  criteria_version: {
    id: "demo-criteria-0001",
    version: 1,
    aggregation: { type: "sum" },
    max_score_total: 2,
    criteria: [
      {
        id: "demo-criterion-0001",
        code: "K1",
        position: 1,
        title: "Смысл понятия",
        description: "Демонстрационный критерий: понятие раскрыто.",
        max_score: 1,
        levels: [],
      },
      {
        id: "demo-criterion-0002",
        code: "K2",
        position: 2,
        title: "Конкретный факт",
        description: "Демонстрационный критерий: приведён конкретный факт.",
        max_score: 1,
        levels: [],
      },
    ],
  },
  evaluation_profile: {
    id: "demo-profile-0001",
    code: "demo-history-v1",
    version: 1,
    model_provider: "demo",
    model_name: "synthetic",
  },
  sources: [],
  limits: {
    max_files: 4,
    max_file_bytes: 8 * 1024 * 1024,
    allowed_mime_types: ["image/jpeg", "image/png", "image/webp"],
    min_answer_chars: 10,
    max_answer_chars: 10000,
  },
  created_at: new Date().toISOString(),
  approved_at: new Date().toISOString(),
};

const DEMO_OCR_TEXT =
  "Синтетический демонстрационный ответ. Понятие раскрыто в общих чертах, " +
  "приведён условный исторический факт для демонстрации интерфейса.";

interface DemoSubmission {
  submission: Submission;
  text: string | null;
  transcriptionVersion: number;
  evaluation: Evaluation | null;
  review: ReviewRequest | null;
  timer: ReturnType<typeof setTimeout> | null;
}

function now(): string {
  return new Date().toISOString();
}

function baseSubmission(input: CreateSubmissionInput): Submission {
  const isText = input.inputMode === "text";
  return {
    id: `demo-${Math.random().toString(36).slice(2, 10)}`,
    status: isText ? "ready_for_evaluation" : "ready_for_recognition",
    input_mode: input.inputMode,
    data_origin: input.dataOrigin,
    exam_configuration_id: input.examConfigurationId,
    exam_configuration_status: "approved",
    created_at: now(),
    updated_at: now(),
    expires_at: null,
    files: isText
      ? []
      : (input.files ?? []).map((file, index) => ({
          id: `demo-file-${index}`,
          page_index: index,
          mime_type: file.type || "image/png",
          size_bytes: file.size,
          width_px: 800,
          height_px: 1000,
          sha256: "0".repeat(64),
        })),
    current_transcription: null,
    recognition: null,
    evaluation: null,
    review_request: null,
    allowed_actions: isText
      ? ["edit_transcription", "evaluate", "delete"]
      : ["recognize", "edit_transcription", "delete"],
    poll_interval_ms: null,
  };
}

function buildEvaluation(sub: Submission, text: string): Evaluation {
  const criteria = CONFIG.criteria_version.criteria;
  const quoteStart = Math.min(0, text.length);
  const quote = text.slice(quoteStart, Math.max(10, Math.min(text.length, 60)));

  const results: CriterionResult[] = criteria.map((criterion, index) => ({
    criterion_id: criterion.id,
    code: criterion.code,
    title: criterion.title,
    position: criterion.position,
    score: index === 0 ? 1 : 0,
    max_score: criterion.max_score,
    confidence: index === 0 ? 0.82 : 0.41,
    rationale:
      index === 0
        ? "Демонстрационное обоснование: фрагмент ответа раскрывает понятие."
        : "Демонстрационное обоснование: конкретный факт не выделен однозначно.",
    uncertainty_note:
      index === 0 ? null : "Демо: уверенность модели низкая, проверьте вручную.",
    flags: index === 0 ? [] : ["LOW_CONFIDENCE", "AMBIGUOUS"],
    evidence: quote
      ? [
          {
            id: `demo-evidence-${criterion.id}`,
            kind: index === 0 ? "supports" : "deficiency",
            char_start: quoteStart,
            char_end: quoteStart + quote.length,
            quote,
            note: "Демонстрационный фрагмент.",
          },
        ]
      : [],
  }));

  const total = results.reduce((sum, item) => sum + item.score, 0);
  return {
    id: `demo-evaluation-${Math.random().toString(36).slice(2, 8)}`,
    submission_id: sub.id,
    status: "succeeded",
    transcription_id: `demo-transcription-${sub.id}`,
    transcription_version: 1,
    is_current: true,
    versions: {
      exam_configuration_id: CONFIG.id,
      exam_configuration_status: "approved",
      exam: {
        code: CONFIG.exam.code,
        version_label: CONFIG.exam.version_label,
        exam_year: CONFIG.exam.exam_year,
      },
      task_version: {
        id: CONFIG.task.task_version_id,
        task_key: CONFIG.task.task_key,
        task_number: CONFIG.task.task_number,
        version: CONFIG.task.version,
        content_sha256: "0".repeat(64),
      },
      criteria_version: {
        id: CONFIG.criteria_version.id,
        version: CONFIG.criteria_version.version,
        content_sha256: "0".repeat(64),
      },
      evaluation_profile: {
        id: CONFIG.evaluation_profile.id,
        code: CONFIG.evaluation_profile.code,
        version: CONFIG.evaluation_profile.version,
        prompt_sha256: "0".repeat(64),
      },
      model: { provider: "demo", requested: "synthetic", reported: "synthetic" },
      source_editions: [],
    },
    total_score: total,
    max_score: CONFIG.criteria_version.max_score_total,
    overall_confidence: 0.41,
    needs_review: true,
    flags: ["LOW_CONFIDENCE", "AMBIGUOUS"],
    summary: "Демонстрационный результат. Это не официальный балл ЕГЭ.",
    criteria: results,
    final: { total_score: total, max_score: CONFIG.criteria_version.max_score_total, source: "model" },
    expert_review: null,
    disclaimer:
      "Демонстрационные данные. Ориентировочная оценка модели не является официальным баллом ЕГЭ.",
    created_at: now(),
  };
}

export function createDemoCheckApi(): CheckApi {
  const store = new Map<string, DemoSubmission>();

  function getRecord(id: UUID, token: string): DemoSubmission {
    const record = store.get(id);
    if (!record || token !== "sbt_demo") {
      throw new ApiError({ code: "NOT_FOUND", message: "Отправка не найдена.", status: 404 });
    }
    return record;
  }

  function snapshot(record: DemoSubmission): Submission {
    return { ...record.submission, updated_at: now() };
  }

  function finishRecognition(record: DemoSubmission): void {
    record.timer = null;
    record.text = DEMO_OCR_TEXT;
    record.transcriptionVersion = 1;
    record.submission = {
      ...record.submission,
      status: "ready_for_evaluation",
      poll_interval_ms: null,
      current_transcription: {
        id: `demo-transcription-${record.submission.id}`,
        version: 1,
        source: "ocr",
        char_count: DEMO_OCR_TEXT.length,
        text_sha256: "0".repeat(64),
        created_at: now(),
      },
      recognition: record.submission.recognition
        ? { ...record.submission.recognition, status: "succeeded", finished_at: now() }
        : null,
      allowed_actions: ["edit_transcription", "evaluate", "delete", "recognize"],
    };
  }

  function finishEvaluation(record: DemoSubmission): void {
    record.timer = null;
    const evaluation = buildEvaluation(record.submission, record.text ?? "");
    record.evaluation = evaluation;
    record.submission = {
      ...record.submission,
      status: "evaluated",
      poll_interval_ms: null,
      evaluation: {
        id: evaluation.id,
        attempt_no: 1,
        status: "succeeded",
        transcription_version: record.transcriptionVersion,
        is_current: true,
        started_at: now(),
        finished_at: now(),
        error: null,
        total_score: evaluation.total_score,
        max_score: evaluation.max_score,
      },
      allowed_actions: ["edit_transcription", "view_result", "request_review", "delete"],
    };
  }

  return {
    mode: "demo",

    async listConfigurations() {
      return [CONFIG];
    },

    async createSubmission(input) {
      const submission = baseSubmission(input);
      const record: DemoSubmission = {
        submission,
        text: input.inputMode === "text" ? (input.text ?? "") : null,
        transcriptionVersion: input.inputMode === "text" ? 1 : 0,
        evaluation: null,
        review: null,
        timer: null,
      };
      if (input.inputMode === "text") {
        submission.current_transcription = {
          id: `demo-transcription-${submission.id}`,
          version: 1,
          source: "manual_input",
          char_count: record.text?.length ?? 0,
          text_sha256: "0".repeat(64),
          created_at: now(),
        };
      }
      store.set(submission.id, record);
      const created: SubmissionCreated = { ...submission, access_token: "sbt_demo" };
      return created;
    },

    async getSubmission(id, token) {
      return snapshot(getRecord(id, token));
    },

    async recognize(id, token) {
      const record = getRecord(id, token);
      if (record.submission.status === "recognizing") return snapshot(record);
      record.submission = {
        ...record.submission,
        status: "recognizing",
        poll_interval_ms: 400,
        recognition: {
          id: `demo-recognition-${id}`,
          attempt_no: 1,
          status: "running",
          engine: "demo",
          engine_version: "0",
          started_at: now(),
          finished_at: null,
          error: null,
          transcription_id: null,
        },
        allowed_actions: [],
      };
      if (record.timer) clearTimeout(record.timer);
      record.timer = setTimeout(() => finishRecognition(record), 600);
      return snapshot(record);
    },

    async getTranscription(id, token) {
      const record = getRecord(id, token);
      if (record.text === null) {
        throw new ApiError({ code: "NOT_FOUND", message: "Текст ещё не распознан.", status: 404 });
      }
      const transcription: Transcription = {
        id: `demo-transcription-${id}`,
        version: record.transcriptionVersion,
        source: record.transcriptionVersion > 1 ? "user_edit" : record.submission.input_mode === "text" ? "manual_input" : "ocr",
        char_count: record.text.length,
        text_sha256: "0".repeat(64),
        created_at: now(),
        text: record.text,
        parent_version: record.transcriptionVersion > 1 ? record.transcriptionVersion - 1 : null,
        ocr: null,
      };
      return transcription;
    },

    async updateTranscription(id, token, _baseVersion, text) {
      const record = getRecord(id, token);
      if (record.text !== text) {
        record.transcriptionVersion += 1;
      }
      record.text = text;
      record.submission = {
        ...record.submission,
        status: "ready_for_evaluation",
        evaluation: null,
        current_transcription: {
          id: `demo-transcription-${id}`,
          version: record.transcriptionVersion,
          source: "user_edit",
          char_count: text.length,
          text_sha256: "0".repeat(64),
          created_at: now(),
        },
        allowed_actions: ["edit_transcription", "evaluate", "delete", "recognize"],
      };
      return this.getTranscription(id, token);
    },

    async evaluate(id, token) {
      const record = getRecord(id, token);
      if (record.submission.status === "evaluating") return snapshot(record);
      record.submission = {
        ...record.submission,
        status: "evaluating",
        poll_interval_ms: 400,
        allowed_actions: [],
        evaluation: {
          id: `demo-evaluation-${id}`,
          attempt_no: 1,
          status: "running",
          transcription_version: record.transcriptionVersion,
          is_current: true,
          started_at: now(),
          finished_at: null,
          error: null,
          total_score: null,
          max_score: null,
        },
      };
      if (record.timer) clearTimeout(record.timer);
      record.timer = setTimeout(() => finishEvaluation(record), 800);
      return snapshot(record);
    },

    async getResult(id, token) {
      const record = getRecord(id, token);
      if (!record.evaluation) {
        throw new ApiError({ code: "RESULT_NOT_READY", message: "Результат ещё не готов.", status: 409 });
      }
      return record.evaluation;
    },

    async requestReview(id, token, payload: RequestReviewPayload) {
      const record = getRecord(id, token);
      if (record.review) return record.review;
      record.review = {
        id: `demo-review-${id}`,
        submission_id: id,
        evaluation_id: record.evaluation?.id ?? "",
        status: "open",
        reason_code: payload.reason_code,
        criterion_codes: payload.criterion_codes,
        comment: payload.comment,
        created_at: now(),
        resolved_at: null,
        decision: null,
      };
      record.submission = {
        ...record.submission,
        review_request: {
          id: record.review.id,
          status: "open",
          created_at: record.review.created_at,
        },
      };
      return record.review;
    },

    async getReviewRequest(id, token) {
      const record = getRecord(id, token);
      if (!record.review) {
        throw new ApiError({ code: "NOT_FOUND", message: "Запрос не найден.", status: 404 });
      }
      return record.review;
    },

    async deleteSubmission(id, token) {
      getRecord(id, token);
      const record = store.get(id);
      if (record?.timer) clearTimeout(record.timer);
      store.delete(id);
    },

    async getFileBlob() {
      throw new ApiError({
        code: "NOT_FOUND",
        message: "В демо-режиме изображения страниц недоступны.",
        status: 404,
      });
    },
  };
}
