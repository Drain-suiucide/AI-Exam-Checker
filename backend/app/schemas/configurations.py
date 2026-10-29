"""Schemas for the public exam-configuration catalogue."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Material(BaseModel):
    kind: Literal["text", "list"]
    title: str
    content: str


class CriterionLevel(BaseModel):
    score: int
    description: str


class Criterion(BaseModel):
    id: str
    code: str
    position: int
    title: str
    description: str
    max_score: int
    levels: list[CriterionLevel]


class ExamInfo(BaseModel):
    code: str
    subject: str
    title: str
    version_label: str
    exam_year: int


class TaskInfo(BaseModel):
    task_version_id: str
    task_key: str
    task_number: str | None
    version: int
    title: str
    statement: str
    materials: list[Material]
    max_score: int


class Aggregation(BaseModel):
    type: Literal["sum"]


class CriteriaInfo(BaseModel):
    id: str
    version: int
    aggregation: Aggregation
    max_score_total: int
    criteria: list[Criterion]


class EvaluationProfileInfo(BaseModel):
    id: str
    code: str
    version: int
    model_provider: str
    model_name: str


class SourceInfo(BaseModel):
    publisher: str
    title: str
    edition_label: str
    url: str | None
    retrieved_at: datetime | None


class ConfigurationLimits(BaseModel):
    max_files: int = Field(gt=0)
    max_file_bytes: int = Field(gt=0)
    allowed_mime_types: list[str]
    min_answer_chars: int = Field(gt=0)
    max_answer_chars: int = Field(gt=0)


class ExamConfigurationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    status: Literal["draft", "approved", "retired"]
    is_default: bool
    exam: ExamInfo
    task: TaskInfo
    criteria_version: CriteriaInfo
    evaluation_profile: EvaluationProfileInfo
    sources: list[SourceInfo]
    limits: ConfigurationLimits
    created_at: datetime
    approved_at: datetime | None


class ConfigurationListResponse(BaseModel):
    items: list[ExamConfigurationResponse]
