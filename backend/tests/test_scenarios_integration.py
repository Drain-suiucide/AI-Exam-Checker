import pytest
from app.services.ocr.validation import validate_image
from app.services.ocr.types import UnsupportedMediaTypeError, ImageTooLargeError, OcrInputError
from app.services.evaluation.engine import EvaluationEngine
from app.schemas.evaluation import CriteriaVersion, CriterionDetails, ScoreVariant, EvaluationResult, CriterionScoreResult
from app.services.evaluation.workflow import ReviewWorkflowService, StateTransitionError, ConcurrencyConflictError, UnauthorizedActionError
from app.schemas.evaluation import WorkflowState, ExpertEvaluationUpdate
from datetime import date
from io import BytesIO
from PIL import Image

def create_image(size=(100, 100), color=(255, 0, 0), format="JPEG"):
    buf = BytesIO()
    img = Image.new("RGB", size, color)
    img.save(buf, format=format)
    return buf.getvalue()

@pytest.fixture
def mock_criteria():
    return CriteriaVersion(
        exam="ЕГЭ",
        year=2026,
        task_id="task_1",
        version_id="v1.0",
        source_url="https://fipi.ru",
        approval_date=date(2026, 1, 1),
        max_score=2,
        criteria=[
            CriterionDetails(
                criterion_id="k1",
                official_description="Исторические факты",
                llm_instruction="Оцени наличие фактов",
                project_rules="",
                diagnostic_hints="",
                score_variants=[
                    ScoreVariant(score=0, condition="Нет"),
                    ScoreVariant(score=1, condition="Частично"),
                    ScoreVariant(score=2, condition="Да")
                ],
                required_evidence="Цитата из текста с фактом",
                ambiguity_rules="На ревью при сомнениях"
            )
        ]
    )

def test_scenario_a_manual_text_evaluation(mock_criteria):
    class ValidLLM:
        def generate(self, answer, criteria, prompt):
            return EvaluationResult(
                total_score=2,
                criterion_scores=[
                    CriterionScoreResult(
                        criterion_id="k1",
                        score=2,
                        evidence_fragment="отмена крепостного права 1861",
                        explanation="Все верно",
                        status="pre_confirmed",
                        used_version_link="v1.0"
                    )
                ],
                overall_status="success",
                version_id="v1.0"
            )

    engine = EvaluationEngine(llm_client=ValidLLM())
    res = engine.evaluate_answer("отмена крепостного права 1861", mock_criteria, "ЕГЭ", 2026, "task_1")
    assert res.overall_status == "success"
    assert res.total_score == 2

def test_scenario_c_ocr_invalid_input():
    with pytest.raises(OcrInputError):
        validate_image(b"")
    with pytest.raises(UnsupportedMediaTypeError):
        validate_image(b"not an image file")

def test_scenario_d_criteria_mismatch(mock_criteria):
    engine = EvaluationEngine(llm_client=None)
    res = engine.evaluate_answer("ответ", mock_criteria, "ЕГЭ", 2025, "task_1")
    assert res.overall_status == "rejected"
    assert "несовместима" in res.review_reason

def test_scenario_e_model_invalid_score(mock_criteria):
    class InvalidScoreLLM:
        def generate(self, answer, criteria, prompt):
            return EvaluationResult(
                total_score=5,
                criterion_scores=[
                    CriterionScoreResult(
                        criterion_id="k1",
                        score=5,
                        evidence_fragment="ответ",
                        explanation="invalid",
                        status="pre_confirmed",
                        used_version_link="v1.0"
                    )
                ],
                overall_status="success",
                version_id="v1.0"
            )
    engine = EvaluationEngine(llm_client=InvalidScoreLLM())
    res = engine.evaluate_answer("ответ", mock_criteria, "ЕГЭ", 2026, "task_1")
    assert res.overall_status == "needs_manual_review"

def test_scenario_f_hallucinated_evidence(mock_criteria):
    class HallucinatingLLM:
        def generate(self, answer, criteria, prompt):
            return EvaluationResult(
                total_score=2,
                criterion_scores=[
                    CriterionScoreResult(
                        criterion_id="k1",
                        score=2,
                        evidence_fragment="несуществующая цитата",
                        explanation="фантазия модели",
                        status="pre_confirmed",
                        used_version_link="v1.0"
                    )
                ],
                overall_status="success",
                version_id="v1.0"
            )
    engine = EvaluationEngine(llm_client=HallucinatingLLM())
    res = engine.evaluate_answer("реальный ответ ученика", mock_criteria, "ЕГЭ", 2026, "task_1")
    assert res.overall_status == "needs_manual_review"
    assert res.criterion_scores[0].status == "needs_review"

def test_scenario_g_expert_workflow():
    service = ReviewWorkflowService()
    state = WorkflowState(
        submission_id="sub_1",
        status="REVIEW_REQUIRED",
        version=1,
        audit_trail=[]
    )
    state = service.start_expert_review(state, expert_id="exp_1", current_version=1)
    assert state.status == "REVIEW_IN_PROGRESS"
    assert state.locked_by_user_id == "exp_1"

    update = ExpertEvaluationUpdate(
        total_score=1,
        criterion_scores=[],
        reasoning="Снижен балл за неточность"
    )
    state = service.modify_evaluation(state, expert_id="exp_1", current_version=2, update=update)
    assert state.status == "COMPLETED"
    assert state.final_evaluation.total_score == 1
    assert len(state.audit_trail) == 2

def test_scenario_h_file_too_large():
    img_data = create_image(size=(100, 100))
    with pytest.raises(ImageTooLargeError):
        validate_image(img_data, max_bytes=10)

def test_scenario_i_unauthorized_and_concurrency():
    service = ReviewWorkflowService()
    state = WorkflowState(
        submission_id="sub_1",
        status="REVIEW_REQUIRED",
        version=1,
        audit_trail=[]
    )
    with pytest.raises(ConcurrencyConflictError):
        service.start_expert_review(state, expert_id="exp_1", current_version=999)

    service.start_expert_review(state, expert_id="exp_1", current_version=1)

    update = ExpertEvaluationUpdate(
        total_score=1,
        criterion_scores=[],
        reasoning="Test"
    )
    with pytest.raises(UnauthorizedActionError):
        service.modify_evaluation(state, expert_id="exp_2", current_version=2, update=update)

def test_scenario_j_provider_failure(mock_criteria):
    class CrashingLLM:
        def generate(self, answer, criteria, prompt):
            raise ConnectionError("Secret API key leaking avoided: connection dropped")

    engine = EvaluationEngine(llm_client=CrashingLLM())
    res = engine.evaluate_answer("ответ", mock_criteria, "ЕГЭ", 2026, "task_1")
    assert res.overall_status == "needs_manual_review"
    assert "Сбой при работе модели" in res.review_reason
