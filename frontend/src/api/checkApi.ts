/**
 * Единый интерфейс API проверки ответа.
 *
 * Реализации:
 * - `httpCheckApi` — реальные запросы `/api/v1` (единственная в production);
 * - демонстрационная (`src/demo/`) — только при явно включённом dev-режиме.
 *
 * Компоненты не должны знать, какая реализация используется, но обязаны
 * показывать пользователю метку демонстрационного режима.
 */
import { ApiError, apiRequest } from "./client";
import type {
  ConfigurationStatusFilter,
  Evaluation,
  ExamConfiguration,
  RequestReviewPayload,
  ReviewRequest,
  Submission,
  SubmissionCreated,
  Transcription,
  UUID,
} from "./types";

export interface CreateSubmissionInput {
  examConfigurationId: UUID;
  dataOrigin: "synthetic" | "anonymized";
  inputMode: "image" | "text";
  text?: string;
  files?: File[];
}

export interface CheckApi {
  readonly mode: "live" | "demo";
  listConfigurations(
    status?: ConfigurationStatusFilter,
    signal?: AbortSignal,
  ): Promise<ExamConfiguration[]>;
  createSubmission(
    input: CreateSubmissionInput,
    idempotencyKey: string,
    signal?: AbortSignal,
  ): Promise<SubmissionCreated>;
  getSubmission(
    id: UUID,
    token: string,
    signal?: AbortSignal,
  ): Promise<Submission>;
  recognize(
    id: UUID,
    token: string,
    force?: boolean,
    signal?: AbortSignal,
  ): Promise<Submission>;
  getTranscription(
    id: UUID,
    token: string,
    version?: number,
    signal?: AbortSignal,
  ): Promise<Transcription>;
  updateTranscription(
    id: UUID,
    token: string,
    baseVersion: number,
    text: string,
    signal?: AbortSignal,
  ): Promise<Transcription>;
  evaluate(
    id: UUID,
    token: string,
    transcriptionVersion?: number,
    signal?: AbortSignal,
  ): Promise<Submission>;
  getResult(
    id: UUID,
    token: string,
    evaluationId?: UUID,
    signal?: AbortSignal,
  ): Promise<Evaluation>;
  requestReview(
    id: UUID,
    token: string,
    payload: RequestReviewPayload,
    signal?: AbortSignal,
  ): Promise<ReviewRequest>;
  getReviewRequest(
    id: UUID,
    token: string,
    signal?: AbortSignal,
  ): Promise<ReviewRequest>;
  deleteSubmission(id: UUID, token: string, signal?: AbortSignal): Promise<void>;
  /** Скачивает нормализованную страницу; заголовок токена нельзя передать в <img>. */
  getFileBlob(
    id: UUID,
    token: string,
    fileId: UUID,
    signal?: AbortSignal,
  ): Promise<Blob>;
}

function submitterHeaders(token: string): Record<string, string> {
  return { "X-Submission-Token": token };
}

function fileExtension(name: string): string {
  const dot = name.lastIndexOf(".");
  return dot >= 0 ? name.slice(dot + 1).toLowerCase() : "";
}

export const httpCheckApi: CheckApi = {
  mode: "live",

  async listConfigurations(status = "approved", signal) {
    const query = status === "approved" ? "" : `?status=${status}`;
    const data = await apiRequest<{ items: ExamConfiguration[] }>(
      `/exam-configurations${query}`,
      { signal },
    );
    return data.items;
  },

  async createSubmission(input, idempotencyKey, signal) {
    const body = new FormData();
    body.append("exam_configuration_id", input.examConfigurationId);
    body.append("data_origin", input.dataOrigin);
    body.append("input_mode", input.inputMode);
    if (input.inputMode === "text") {
      body.append("text", input.text ?? "");
    } else {
      for (const file of input.files ?? []) {
        body.append("files", file, file.name || `page.${fileExtension(file.type) || "bin"}`);
      }
    }

    return apiRequest<SubmissionCreated>("/submissions", {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body,
      signal,
      timeoutMs: 30000,
    });
  },

  async getSubmission(id, token, signal) {
    return apiRequest<Submission>(`/submissions/${id}`, {
      headers: submitterHeaders(token),
      signal,
    });
  },

  async recognize(id, token, force = false, signal) {
    return apiRequest<Submission>(`/submissions/${id}/recognize`, {
      method: "POST",
      headers: {
        ...submitterHeaders(token),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ force }),
      signal,
      timeoutMs: 5000,
    });
  },

  async getTranscription(id, token, version, signal) {
    const query = version === undefined ? "" : `?version=${version}`;
    return apiRequest<Transcription>(`/submissions/${id}/transcription${query}`, {
      headers: submitterHeaders(token),
      signal,
    });
  },

  async updateTranscription(id, token, baseVersion, text, signal) {
    return apiRequest<Transcription>(`/submissions/${id}/transcription`, {
      method: "PATCH",
      headers: {
        ...submitterHeaders(token),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ base_version: baseVersion, text }),
      signal,
      timeoutMs: 5000,
    });
  },

  async evaluate(id, token, transcriptionVersion, signal) {
    return apiRequest<Submission>(`/submissions/${id}/evaluate`, {
      method: "POST",
      headers: {
        ...submitterHeaders(token),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(
        transcriptionVersion === undefined
          ? {}
          : { transcription_version: transcriptionVersion },
      ),
      signal,
      timeoutMs: 5000,
    });
  },

  async getResult(id, token, evaluationId, signal) {
    const query = evaluationId ? `?evaluation_id=${evaluationId}` : "";
    return apiRequest<Evaluation>(`/submissions/${id}/result${query}`, {
      headers: submitterHeaders(token),
      signal,
    });
  },

  async requestReview(id, token, payload, signal) {
    return apiRequest<ReviewRequest>(`/submissions/${id}/review-requests`, {
      method: "POST",
      headers: {
        ...submitterHeaders(token),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
      signal,
    });
  },

  async getReviewRequest(id, token, signal) {
    return apiRequest<ReviewRequest>(`/review-requests/${id}`, {
      headers: submitterHeaders(token),
      signal,
    });
  },

  async deleteSubmission(id, token, signal) {
    try {
      await apiRequest<void>(`/submissions/${id}`, {
        method: "DELETE",
        headers: submitterHeaders(token),
        signal,
      });
    } catch (error) {
      // Повторное удаление отвечает 404 — для клиента это успех (§1.4).
      if (error instanceof ApiError && error.status === 404) return;
      throw error;
    }
  },

  async getFileBlob(id, token, fileId, signal) {
    const response = await fetch(
      `/api/v1/submissions/${id}/files/${fileId}/content`,
      {
        headers: submitterHeaders(token),
        signal,
        cache: "no-store",
      },
    );
    if (!response.ok) {
      throw new ApiError({
        code: `HTTP_${response.status}`,
        message: "Не удалось загрузить изображение страницы.",
        status: response.status,
      });
    }
    return response.blob();
  },
};
