import copy
from datetime import UTC, datetime
from typing import Any

from app.schemas.evaluation import (
    AuditLogEntry,
    EvaluationResult,
    ExpertEvaluationUpdate,
    WorkflowState,
    WorkflowStatus,
)


class StateTransitionError(Exception):
    pass


class ConcurrencyConflictError(Exception):
    pass


class UnauthorizedActionError(Exception):
    pass


class ReviewWorkflowService:
    """Service to handle state transitions for the review workflow."""

    def __init__(self):
        # В реальном приложении здесь был бы репозиторий для доступа к БД
        pass

    def _add_audit_log(
        self,
        state: WorkflowState,
        user_id: str,
        action: str,
        previous_state: dict[str, Any] | None = None,
        new_state: dict[str, Any] | None = None,
        reasoning: str | None = None,
    ):
        log = AuditLogEntry(
            user_id=user_id,
            action=action,
            previous_state=previous_state,
            new_state=new_state,
            reasoning=reasoning,
        )
        state.audit_trail.append(log)

    def transition_status(
        self,
        state: WorkflowState,
        current_version: int,
        new_status: WorkflowStatus,
        user_id: str,
        action_name: str,
        required_role: str = "system",
        reasoning: str | None = None,
    ):
        """Generic state transition logic with concurrency check."""
        # 1. Optimistic Concurrency Control
        if state.version != current_version:
            raise ConcurrencyConflictError(
                "Document version mismatch. Another user may have updated it."
            )

        # 2. Check roles (simplified logic)
        # В реальной системе здесь будет проверка RBAC
        if required_role == "expert" and user_id == "system":
            raise UnauthorizedActionError("Experts only.")

        # 3. Apply changes
        old_status = state.status
        state.status = new_status
        state.version += 1

        # 4. Audit
        self._add_audit_log(
            state=state,
            user_id=user_id,
            action=action_name,
            previous_state={"status": old_status},
            new_state={"status": new_status},
            reasoning=reasoning,
        )

    def start_expert_review(
        self, state: WorkflowState, expert_id: str, current_version: int
    ) -> WorkflowState:
        """Эсперт берет работу на проверку."""
        if state.status != "REVIEW_REQUIRED":
            raise StateTransitionError(f"Cannot start review from status {state.status}")

        if state.locked_by_user_id and state.locked_by_user_id != expert_id:
            raise StateTransitionError("Document is locked by another expert.")

        self.transition_status(
            state=state,
            current_version=current_version,
            new_status="REVIEW_IN_PROGRESS",
            user_id=expert_id,
            action_name="EXPERT_REVIEW_STARTED",
            required_role="expert",
        )
        state.locked_by_user_id = expert_id
        state.locked_at = datetime.now(UTC).replace(tzinfo=None)
        return state

    def accept_ai_evaluation(
        self, state: WorkflowState, expert_id: str, current_version: int
    ) -> WorkflowState:
        """Эксперт принимает оценку AI без изменений."""
        if state.status != "REVIEW_IN_PROGRESS":
            raise StateTransitionError("Review must be in progress to accept.")

        if state.locked_by_user_id != expert_id:
            raise UnauthorizedActionError("Document is locked by another expert.")

        self.transition_status(
            state=state,
            current_version=current_version,
            new_status="COMPLETED",
            user_id=expert_id,
            action_name="AI_SCORE_ACCEPTED",
            required_role="expert",
        )

        # Финальный результат равен результату ИИ
        state.final_evaluation = copy.deepcopy(state.ai_evaluation)

        # Снимаем блокировку
        state.locked_by_user_id = None
        state.locked_at = None
        return state

    def modify_evaluation(
        self,
        state: WorkflowState,
        expert_id: str,
        current_version: int,
        update: ExpertEvaluationUpdate,
    ) -> WorkflowState:
        """Эксперт изменяет оценку и обосновывает её."""
        if state.status != "REVIEW_IN_PROGRESS":
            raise StateTransitionError("Review must be in progress to modify.")

        if state.locked_by_user_id != expert_id:
            raise UnauthorizedActionError("Document is locked by another expert.")

        if not update.reasoning:
            raise ValueError("Reasoning is required for modification.")

        state.ai_evaluation.model_dump() if state.ai_evaluation else None

        self.transition_status(
            state=state,
            current_version=current_version,
            new_status="COMPLETED",
            user_id=expert_id,
            action_name="SCORE_MODIFIED",
            required_role="expert",
            reasoning=update.reasoning,
        )

        # Создаем новый EvaluationResult на основе обновления
        new_eval = EvaluationResult(
            total_score=update.total_score,
            criterion_scores=update.criterion_scores,
            overall_status="success",  # После ручной проверки статус успешен
            version_id=state.ai_evaluation.version_id if state.ai_evaluation else "manual",
            review_reason=update.reasoning,
        )

        state.expert_evaluation = new_eval
        state.final_evaluation = new_eval

        # Снимаем блокировку
        state.locked_by_user_id = None
        state.locked_at = None

        return state
