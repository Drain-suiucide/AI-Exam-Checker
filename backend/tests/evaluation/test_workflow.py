import pytest
from datetime import datetime
from pydantic import ValidationError

from app.schemas.evaluation import (
    WorkflowState,
    AuditLogEntry,
    ExpertEvaluationUpdate,
    EvaluationResult,
    CriterionScoreResult
)

def test_workflow_state_initialization():
    state = WorkflowState(submission_id="sub-123", status="RECEIVED")
    assert state.status == "RECEIVED"
    assert state.version == 1
    assert state.ai_evaluation is None
    assert state.expert_evaluation is None
    assert len(state.audit_trail) == 0

def test_audit_log_entry():
    entry = AuditLogEntry(
        user_id="expert_1",
        action="SCORE_MODIFIED",
        reasoning="Changed score due to misinterpretation."
    )
    assert entry.user_id == "expert_1"
    assert entry.action == "SCORE_MODIFIED"
    assert entry.reasoning == "Changed score due to misinterpretation."
    assert isinstance(entry.timestamp, datetime)

def test_expert_evaluation_update_requires_reasoning():
    # Attempt to create an update without reasoning
    with pytest.raises(ValidationError):
        ExpertEvaluationUpdate(
            criterion_scores=[],
            total_score=5
        )

def test_expert_evaluation_update_valid():
    score_result = CriterionScoreResult(
        criterion_id="crit_1",
        score=2,
        explanation="Valid point",
        status="pre_confirmed",
        used_version_link="http://example.com/v1"
    )
    update = ExpertEvaluationUpdate(
        criterion_scores=[score_result],
        total_score=2,
        reasoning="Correcting AI misjudgement."
    )
    assert update.total_score == 2
    assert update.reasoning == "Correcting AI misjudgement."
