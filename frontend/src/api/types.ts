/**
 * Типы данных API по API_CONTRACT.md (v1).
 *
 * ВАЖНО: контракт (§4.4) требует генерировать типы из `docs/openapi.json`
 * (`openapi-typescript`). Файл OpenAPI ещё не экспортирован backend-ом,
 * поэтому типы написаны вручную строго по API_CONTRACT.md и подлежат
 * замене на сгенерированные, когда появится openapi.json.
 */

export type UUID = string;
/** ISO 8601 UTC, например "2026-10-26T12:00:00Z". */
export type Timestamp = string;
/** Самооценка модели 0.00–1.00; не калиброванная вероятность. */
export type Confidence = number;
export type Sha256 = string;

export type SubmissionStatus =
  | "ready_for_recognition"
  | "recognizing"
  | "recognition_failed"
  | "ready_for_evaluation"
  | "evaluating"
  | "evaluation_failed"
  | "evaluated";

export type Action =
  | "recognize"
  | "edit_transcription"
  | "evaluate"
  | "view_result"
  | "request_review"
  | "delete";

export type Flag =
  | "LOW_CONFIDENCE"
  | "NO_EVIDENCE_FOUND"
  | "AMBIGUOUS"
  | "OCR_LOW_QUALITY";

export interface ApiErrorBody {
  code: string;
  message: string;
}

export interface ExamConfiguration {
  id: UUID;
  slug: string;
  status: "draft" | "approved" | "retired";
  is_default: boolean;
  exam: {
    code: string;
    subject: string;
    title: string;
    version_label: string;
    exam_year: number;
  };
  task: {
    task_version_id: UUID;
    task_key: string;
    task_number: string | null;
    version: number;
    title: string;
    statement: string;
    materials: { kind: "text" | "list"; title: string; content: string }[];
    max_score: number;
  };
  criteria_version: {
    id: UUID;
    version: number;
    aggregation: { type: "sum" };
    max_score_total: number;
    criteria: {
      id: UUID;
      code: string;
      position: number;
      title: string;
      description: string;
      max_score: number;
      levels: { score: number; description: string }[];
    }[];
  };
  evaluation_profile: {
    id: UUID;
    code: string;
    version: number;
    model_provider: string;
    model_name: string;
  };
  sources: {
    publisher: string;
    title: string;
    edition_label: string;
    url: string | null;
    retrieved_at: Timestamp | null;
  }[];
  limits: {
    max_files: number;
    max_file_bytes: number;
    allowed_mime_types: string[];
    min_answer_chars: number;
    max_answer_chars: number;
  };
  created_at: Timestamp;
  approved_at: Timestamp | null;
}

export interface FileInfo {
  id: UUID;
  page_index: number;
  mime_type: string;
  size_bytes: number;
  width_px: number;
  height_px: number;
  sha256: Sha256;
}

export interface RecognitionRun {
  id: UUID;
  attempt_no: number;
  status: "running" | "succeeded" | "failed";
  engine: string;
  engine_version: string;
  started_at: Timestamp;
  finished_at: Timestamp | null;
  error: ApiErrorBody | null;
  transcription_id: UUID | null;
}

export interface EvaluationSummary {
  id: UUID;
  attempt_no: number;
  status: "running" | "succeeded" | "failed";
  transcription_version: number;
  is_current: boolean;
  started_at: Timestamp;
  finished_at: Timestamp | null;
  error: ApiErrorBody | null;
  total_score: number | null;
  max_score: number | null;
}

export interface ReviewRequestSummary {
  id: UUID;
  status: "open" | "resolved";
  created_at: Timestamp;
}

export interface Submission {
  id: UUID;
  status: SubmissionStatus;
  input_mode: "image" | "text";
  data_origin: "synthetic" | "anonymized";
  exam_configuration_id: UUID;
  exam_configuration_status: "draft" | "approved" | "retired";
  created_at: Timestamp;
  updated_at: Timestamp;
  expires_at: Timestamp | null;
  files: FileInfo[];
  current_transcription: TranscriptionSummary | null;
  recognition: RecognitionRun | null;
  evaluation: EvaluationSummary | null;
  review_request: ReviewRequestSummary | null;
  allowed_actions: Action[];
  poll_interval_ms: number | null;
}

export interface SubmissionCreated extends Submission {
  access_token: string;
}

export interface TranscriptionSummary {
  id: UUID;
  version: number;
  source: "ocr" | "manual_input" | "user_edit";
  char_count: number;
  text_sha256: Sha256;
  created_at: Timestamp;
}

export interface Transcription extends TranscriptionSummary {
  text: string;
  parent_version: number | null;
  ocr: {
    mean_confidence: Confidence | null;
    segments: {
      index: number;
      page_index: number;
      char_start: number;
      char_end: number;
      confidence: Confidence | null;
      bbox: [number, number, number, number] | null;
    }[];
  } | null;
}

export interface EvidenceRef {
  id: UUID;
  kind: "supports" | "deficiency";
  char_start: number;
  char_end: number;
  quote: string;
  note: string | null;
}

export interface CriterionResult {
  criterion_id: UUID;
  code: string;
  title: string;
  position: number;
  score: number;
  max_score: number;
  confidence: Confidence;
  rationale: string;
  uncertainty_note: string | null;
  flags: Flag[];
  evidence: EvidenceRef[];
}

export interface VersionStamp {
  exam_configuration_id: UUID;
  exam_configuration_status: "draft" | "approved" | "retired";
  exam: { code: string; version_label: string; exam_year: number };
  task_version: {
    id: UUID;
    task_key: string;
    task_number: string | null;
    version: number;
    content_sha256: Sha256;
  };
  criteria_version: { id: UUID; version: number; content_sha256: Sha256 };
  evaluation_profile: {
    id: UUID;
    code: string;
    version: number;
    prompt_sha256: Sha256;
  };
  model: { provider: string; requested: string; reported: string | null };
  source_editions: {
    publisher: string;
    title: string;
    edition_label: string;
    url: string | null;
  }[];
}

export type ReviewReasonCode =
  | "disagree_with_score"
  | "ocr_error"
  | "unclear_rationale"
  | "other";

export interface ReviewRequest {
  id: UUID;
  submission_id: UUID;
  evaluation_id: UUID;
  status: "open" | "resolved";
  reason_code: ReviewReasonCode;
  criterion_codes: string[];
  comment: string | null;
  created_at: Timestamp;
  resolved_at: Timestamp | null;
  decision: ExpertDecision | null;
}

export interface ExpertDecision {
  id: UUID;
  review_request_id: UUID;
  outcome: "confirmed" | "adjusted";
  criterion_adjustments: {
    criterion_code: string;
    original_score: number;
    score: number;
    comment: string | null;
  }[];
  final_total_score: number;
  max_score: number;
  comment: string;
  decided_by: string;
  decided_at: Timestamp;
}

export interface Evaluation {
  id: UUID;
  submission_id: UUID;
  status: "succeeded";
  transcription_id: UUID;
  transcription_version: number;
  is_current: boolean;
  versions: VersionStamp;
  total_score: number;
  max_score: number;
  overall_confidence: Confidence;
  needs_review: boolean;
  flags: Flag[];
  summary: string | null;
  criteria: CriterionResult[];
  final: {
    total_score: number;
    max_score: number;
    source: "model" | "expert";
  };
  expert_review: ReviewRequest | null;
  disclaimer: string;
  created_at: Timestamp;
}

export interface RequestReviewPayload {
  evaluation_id: UUID | null;
  reason_code: ReviewReasonCode;
  criterion_codes: string[];
  comment: string | null;
}

/** Query-параметр status у GET /exam-configurations. */
export type ConfigurationStatusFilter = "approved" | "draft" | "all";
