from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Literal
from datetime import date

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
    evidence_fragment: Optional[str] = Field(description="Доказательный фрагмент из ответа")
    explanation: str
    status: Literal["pre_confirmed", "ambiguous", "needs_review"]
    used_version_link: str

class EvaluationResult(BaseModel):
    total_score: int
    criterion_scores: List[CriterionScoreResult]
    overall_status: Literal["success", "needs_manual_review", "rejected"]
    version_id: str
    review_reason: Optional[str] = None
