from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Literal, Dict, Any
from datetime import date, datetime, timezone
import uuid

# --- Существующие схемы ---

class ScoreVariant(BaseModel):
    score: int
    condition: str

class CriterionDetails(BaseModel):
    criterion_id: str
    official_description: str = Field(description="Официальная формулировка (ФИПИ)")
    llm_instruction: str = Field(description="Внутренняя инструкция для языковой модели")
    project_rules: str = Field(description="Проектные правила оценивания")
    diagnostic_hints: str = Field(description="Диагностические подсказки для объяснения")
    score_variants: List[ScoreVariant]
    required_evidence: str
    ambiguity_rules: str

class CriteriaVersion(BaseModel):
    exam: str
    year: int
    task_id: str
    version_id: str
    source_url: str
    approval_date: date
    max_score: int
    criteria: List[CriterionDetails]
    manual_review_triggers: List[str] = Field(default_factory=list)

class CriterionScoreResult(BaseModel):
    criterion_id: str
    score: int
    evidence_fragment: Optional[str] = Field(None, description="Доказательный фрагмент из ответа")
    explanation: str
    status: Literal["pre_confirmed", "ambiguous", "needs_review"]
    used_version_link: str

class EvaluationResult(BaseModel):
    total_score: int
    criterion_scores: List[CriterionScoreResult]
    overall_status: Literal["success", "needs_manual_review", "rejected"]
    version_id: str
    review_reason: Optional[str] = None

# --- Новые схемы для Expert Review Workflow ---

WorkflowStatus = Literal[
    "RECEIVED",
    "OCR_PENDING",
    "TRANSCRIPTION_REVIEW",
    "READY_FOR_EVALUATION",
    "EVALUATION_PENDING",
    "REVIEW_REQUIRED",
    "REVIEW_IN_PROGRESS",
    "COMPLETED",
    "FAILED",
]

class AuditLogEntry(BaseModel):
    log_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    user_id: str = Field(description="ID пользователя или 'system'")
    action: str = Field(description="Тип действия (например, SCORE_MODIFIED)")
    previous_state: Optional[Dict[str, Any]] = None
    new_state: Optional[Dict[str, Any]] = None
    reasoning: Optional[str] = Field(None, description="Обоснование эксперта")

class ExpertEvaluationUpdate(BaseModel):
    criterion_scores: List[CriterionScoreResult]
    total_score: int
    reasoning: str = Field(..., description="Обязательное обоснование изменения оценок")

class WorkflowState(BaseModel):
    submission_id: str
    status: WorkflowStatus
    version: int = Field(default=1, description="Для оптимистичных блокировок")

    # Данные OCR
    image_url: Optional[HttpUrl] = None
    transcription: Optional[str] = None

    # Оценки
    ai_evaluation: Optional[EvaluationResult] = Field(None, description="Оригинальный результат модели (immutable)")
    expert_evaluation: Optional[EvaluationResult] = Field(None, description="Результат проверки экспертом")
    final_evaluation: Optional[EvaluationResult] = Field(None, description="Итоговый результат")

    # Блокировка
    locked_by_user_id: Optional[str] = None
    locked_at: Optional[datetime] = None

    # Аудит
    audit_trail: List[AuditLogEntry] = Field(default_factory=list)
