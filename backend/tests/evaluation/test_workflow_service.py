import pytest
from pydantic import ValidationError

from app.schemas.evaluation import WorkflowState, ExpertEvaluationUpdate, CriterionScoreResult, EvaluationResult
from app.services.evaluation.workflow import (
    ReviewWorkflowService,
    StateTransitionError,
    ConcurrencyConflictError,
    UnauthorizedActionError
)

@pytest.fixture
def service():
    return ReviewWorkflowService()

@pytest.fixture
def base_state():
    ai_eval = EvaluationResult(
        total_score=10,
        criterion_scores=[],
        overall_status="needs_manual_review",
        version_id="v1"
    )
    return WorkflowState(
        submission_id="sub-1",
        status="REVIEW_REQUIRED",
        version=1,
        ai_evaluation=ai_eval
    )

def test_start_expert_review_success(service, base_state):
    updated_state = service.start_expert_review(base_state, expert_id="exp_1", current_version=1)

    assert updated_state.status == "REVIEW_IN_PROGRESS"
    assert updated_state.version == 2
    assert updated_state.locked_by_user_id == "exp_1"
    assert updated_state.locked_at is not None

    log = updated_state.audit_trail[-1]
    assert log.action == "EXPERT_REVIEW_STARTED"
    assert log.user_id == "exp_1"

def test_start_expert_review_concurrency_conflict(service, base_state):
    # Simulate a version mismatch
    with pytest.raises(ConcurrencyConflictError):
        service.start_expert_review(base_state, expert_id="exp_1", current_version=0)

def test_start_expert_review_wrong_state(service, base_state):
    base_state.status = "RECEIVED"
    with pytest.raises(StateTransitionError, match="Cannot start review"):
        service.start_expert_review(base_state, expert_id="exp_1", current_version=1)

def test_modify_evaluation_success(service, base_state):
    # First, start the review
    state = service.start_expert_review(base_state, expert_id="exp_1", current_version=1)

    # Then modify it
    update = ExpertEvaluationUpdate(
        criterion_scores=[],
        total_score=8,
        reasoning="The AI hallucinated a fact."
    )

    final_state = service.modify_evaluation(state, expert_id="exp_1", current_version=2, update=update)

    assert final_state.status == "COMPLETED"
    assert final_state.version == 3
    assert final_state.expert_evaluation.total_score == 8
    assert final_state.final_evaluation.total_score == 8
    assert final_state.locked_by_user_id is None # Lock should be released

    log = final_state.audit_trail[-1]
    assert log.action == "SCORE_MODIFIED"
    assert log.reasoning == "The AI hallucinated a fact."

def test_modify_evaluation_locked_by_other(service, base_state):
    # Start review as exp_1
    state = service.start_expert_review(base_state, expert_id="exp_1", current_version=1)

    update = ExpertEvaluationUpdate(
        criterion_scores=[],
        total_score=8,
        reasoning="Should fail."
    )

    # Try to modify as exp_2
    with pytest.raises(UnauthorizedActionError):
        service.modify_evaluation(state, expert_id="exp_2", current_version=2, update=update)
