"""Database models for the AI Exam Checker backend."""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OfficialSource(Base):
    __tablename__ = "official_sources"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    publisher: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_editions: Mapped[list["SourceEdition"]] = relationship(back_populates="source")
    __table_args__ = (UniqueConstraint("publisher", "title"),)


class SourceEdition(Base):
    __tablename__ = "source_editions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("official_sources.id", ondelete="CASCADE"))
    edition_label: Mapped[str] = mapped_column(String(64), nullable=False)
    published_at: Mapped[date] = mapped_column(Date, nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    url: Mapped[str | None] = mapped_column(String(2048))
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[OfficialSource] = relationship(back_populates="source_editions")


class ExamVersion(Base):
    __tablename__ = "exam_versions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    edition_id: Mapped[str] = mapped_column(ForeignKey("source_editions.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    subject: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    version_label: Mapped[str] = mapped_column(String(64), nullable=False)
    exam_year: Mapped[int] = mapped_column(Integer, nullable=False)
    task_versions: Mapped[list["TaskVersion"]] = relationship(back_populates="exam_version")
    configurations: Mapped[list["ExamConfiguration"]] = relationship(back_populates="exam_version")


class TaskVersion(Base):
    __tablename__ = "task_versions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    exam_version_id: Mapped[str] = mapped_column(ForeignKey("exam_versions.id", ondelete="CASCADE"))
    task_key: Mapped[str] = mapped_column(String(255), nullable=False)
    task_number: Mapped[str | None] = mapped_column(String(32))
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    materials: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    max_score: Mapped[int] = mapped_column(Integer, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    exam_version: Mapped[ExamVersion] = relationship(back_populates="task_versions")
    criteria_versions: Mapped[list["CriteriaVersion"]] = relationship(back_populates="task_version")
    configurations: Mapped[list["ExamConfiguration"]] = relationship(back_populates="task_version")


class CriteriaVersion(Base):
    __tablename__ = "criteria_versions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_version_id: Mapped[str] = mapped_column(ForeignKey("task_versions.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    aggregation: Mapped[str] = mapped_column(String(16), nullable=False, default="sum")
    max_score_total: Mapped[int] = mapped_column(Integer, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="approved")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    task_version: Mapped[TaskVersion] = relationship(back_populates="criteria_versions")
    criteria: Mapped[list["Criterion"]] = relationship(back_populates="criteria_version")
    configurations: Mapped[list["ExamConfiguration"]] = relationship(
        back_populates="criteria_version"
    )


class Criterion(Base):
    __tablename__ = "criteria"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    version_id: Mapped[str] = mapped_column(ForeignKey("criteria_versions.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    max_score: Mapped[int] = mapped_column(Integer, nullable=False)
    levels: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    criteria_version: Mapped[CriteriaVersion] = relationship(back_populates="criteria")
    scores: Mapped[list["CriterionScore"]] = relationship(back_populates="criterion")
    __table_args__ = (UniqueConstraint("version_id", "code"),)


class EvaluationProfile(Base):
    __tablename__ = "evaluation_profiles"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    model_provider: Mapped[str] = mapped_column(String(128), nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    configurations: Mapped[list["ExamConfiguration"]] = relationship(
        back_populates="evaluation_profile"
    )


class ExamConfiguration(Base):
    __tablename__ = "exam_configurations"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="approved")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    exam_version_id: Mapped[str] = mapped_column(ForeignKey("exam_versions.id", ondelete="CASCADE"))
    task_version_id: Mapped[str] = mapped_column(ForeignKey("task_versions.id", ondelete="CASCADE"))
    criteria_version_id: Mapped[str] = mapped_column(
        ForeignKey("criteria_versions.id", ondelete="CASCADE")
    )
    evaluation_profile_id: Mapped[str] = mapped_column(
        ForeignKey("evaluation_profiles.id", ondelete="CASCADE")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(String(255))
    exam_version: Mapped[ExamVersion] = relationship(back_populates="configurations")
    task_version: Mapped[TaskVersion] = relationship(back_populates="configurations")
    criteria_version: Mapped[CriteriaVersion] = relationship(back_populates="configurations")
    evaluation_profile: Mapped[EvaluationProfile] = relationship(back_populates="configurations")
    submissions: Mapped[list["Submission"]] = relationship(back_populates="exam_configuration")


class Submission(Base):
    __tablename__ = "submissions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ready_for_recognition")
    input_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    data_origin: Mapped[str] = mapped_column(String(32), nullable=False)
    exam_configuration_id: Mapped[str] = mapped_column(
        ForeignKey("exam_configurations.id", ondelete="CASCADE")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_transcription_id: Mapped[str | None] = mapped_column(
        ForeignKey("transcriptions.id", ondelete="SET NULL")
    )
    evaluation_id: Mapped[str | None] = mapped_column(
        ForeignKey("evaluations.id", ondelete="SET NULL")
    )
    latest_evaluation_attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    exam_configuration: Mapped[ExamConfiguration] = relationship(back_populates="submissions")
    files: Mapped[list["UploadedFile"]] = relationship(back_populates="submission")
    transcriptions: Mapped[list["Transcription"]] = relationship(
        back_populates="submission", foreign_keys="Transcription.submission_id"
    )
    evaluations: Mapped[list["Evaluation"]] = relationship(
        back_populates="submission", foreign_keys="Evaluation.submission_id"
    )
    recognition_runs: Mapped[list["RecognitionRun"]] = relationship(back_populates="submission")
    review_requests: Mapped[list["ReviewRequest"]] = relationship(back_populates="submission")
    __table_args__ = (Index("ix_submissions_expires_at", "expires_at"),)


class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    submission_id: Mapped[str] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"))
    file_key: Mapped[str] = mapped_column(String(512), nullable=False)
    page_index: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    width_px: Mapped[int | None] = mapped_column(Integer)
    height_px: Mapped[int | None] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    submission: Mapped[Submission] = relationship(back_populates="files")


class RecognitionRun(Base):
    __tablename__ = "recognition_runs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    submission_id: Mapped[str] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"))
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    engine: Mapped[str] = mapped_column(String(128), nullable=False)
    engine_version: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[dict | None] = mapped_column(JSONB)
    transcription_id: Mapped[str | None] = mapped_column(
        ForeignKey("transcriptions.id", ondelete="SET NULL")
    )
    submission: Mapped[Submission] = relationship(back_populates="recognition_runs")


class Transcription(Base):
    __tablename__ = "transcriptions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    submission_id: Mapped[str] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    text_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_version: Mapped[int | None] = mapped_column(Integer)
    ocr_data: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    submission: Mapped[Submission] = relationship(
        back_populates="transcriptions", foreign_keys=[submission_id]
    )


class Evaluation(Base):
    __tablename__ = "evaluations"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    submission_id: Mapped[str] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"))
    transcription_id: Mapped[str] = mapped_column(
        ForeignKey("transcriptions.id", ondelete="CASCADE")
    )
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    error: Mapped[dict | None] = mapped_column(JSONB)
    total_score: Mapped[int | None] = mapped_column(Integer)
    max_score: Mapped[int | None] = mapped_column(Integer)
    overall_confidence: Mapped[float | None] = mapped_column(String(10))
    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    flags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    summary: Mapped[str | None] = mapped_column(Text)
    final_source: Mapped[str] = mapped_column(String(16), nullable=False, default="model")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submission: Mapped[Submission] = relationship(
        back_populates="evaluations", foreign_keys=[submission_id]
    )
    criterion_scores: Mapped[list["CriterionScore"]] = relationship(back_populates="evaluation")


class CriterionScore(Base):
    __tablename__ = "criterion_scores"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    evaluation_id: Mapped[str] = mapped_column(ForeignKey("evaluations.id", ondelete="CASCADE"))
    criterion_id: Mapped[str] = mapped_column(ForeignKey("criteria.id", ondelete="CASCADE"))
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(String(10), nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text)
    uncertainty_note: Mapped[str | None] = mapped_column(Text)
    flags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    evaluation: Mapped[Evaluation] = relationship(back_populates="criterion_scores")
    criterion: Mapped[Criterion] = relationship(back_populates="scores")
    evidence_refs: Mapped[list["EvidenceRef"]] = relationship(back_populates="criterion_score")


class EvidenceRef(Base):
    __tablename__ = "evidence_refs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    criterion_score_id: Mapped[str] = mapped_column(
        ForeignKey("criterion_scores.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    char_start: Mapped[int] = mapped_column(Integer, nullable=False)
    char_end: Mapped[int] = mapped_column(Integer, nullable=False)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    criterion_score: Mapped[CriterionScore] = relationship(back_populates="evidence_refs")


class ReviewRequest(Base):
    __tablename__ = "review_requests"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    submission_id: Mapped[str] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"))
    evaluation_id: Mapped[str] = mapped_column(ForeignKey("evaluations.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    reason_code: Mapped[str] = mapped_column(String(32), nullable=False)
    criterion_codes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submission: Mapped[Submission] = relationship(back_populates="review_requests")
    expert_decisions: Mapped[list["ExpertDecision"]] = relationship(back_populates="review_request")


class ExpertDecision(Base):
    __tablename__ = "expert_decisions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    review_request_id: Mapped[str] = mapped_column(
        ForeignKey("review_requests.id", ondelete="CASCADE")
    )
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    criterion_adjustments: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    final_total_score: Mapped[int] = mapped_column(Integer, nullable=False)
    max_score: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    decided_by: Mapped[str] = mapped_column(String(255), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    review_request: Mapped[ReviewRequest] = relationship(back_populates="expert_decisions")


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_ref: Mapped[str | None] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(64))
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    __table_args__ = (Index("ix_audit_log_occurred_at", "occurred_at"),)
