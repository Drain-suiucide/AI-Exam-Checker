import pytest
from datetime import date
from app.schemas.evaluation import CriteriaVersion, CriterionDetails, ScoreVariant, EvaluationResult, CriterionScoreResult
from app.services.evaluation.engine import EvaluationEngine

class MockLLMClient:
    def __init__(self, mock_result=None, should_fail=False):
        self.mock_result = mock_result
        self.should_fail = should_fail

    def generate(self, student_answer, criteria, system_prompt):
        if self.should_fail:
            raise ValueError("LLM connection error")
        return self.mock_result

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
                official_description="Основной критерий",
                llm_instruction="Оцени по К1",
                project_rules="",
                diagnostic_hints="",
                score_variants=[ScoreVariant(score=0, condition="Нет"), ScoreVariant(score=1, condition="Частично"), ScoreVariant(score=2, condition="Да")],
                required_evidence="Цитата из текста",
                ambiguity_rules="На ревью"
            )
        ]
    )

def test_incompatible_criteria_version(mock_criteria):
    engine = EvaluationEngine()
    result = engine.evaluate_answer("Ответ", mock_criteria, "ОГЭ", 2026, "task_1")
    assert result.overall_status == "rejected"
    assert "несовместима" in result.review_reason

def test_empty_answer_triggers_manual_review(mock_criteria):
    engine = EvaluationEngine()
    result = engine.evaluate_answer("   ", mock_criteria, "ЕГЭ", 2026, "task_1")
    assert result.overall_status == "needs_manual_review"
    assert "Пустой ответ" in result.review_reason

def test_llm_hallucinated_evidence(mock_criteria):
    llm_result = EvaluationResult(
        total_score=2,
        criterion_scores=[
            CriterionScoreResult(
                criterion_id="k1",
                score=2,
                evidence_fragment="Галлюцинация",
                explanation="Объяснение",
                status="pre_confirmed",
                used_version_link="v1.0"
            )
        ],
        overall_status="success",
        version_id="v1.0",
        review_reason=None
    )
    engine = EvaluationEngine(llm_client=MockLLMClient(mock_result=llm_result))
    result = engine.evaluate_answer("Мой реальный ответ", mock_criteria, "ЕГЭ", 2026, "task_1")
    assert result.overall_status == "needs_manual_review"
    assert result.criterion_scores[0].status == "needs_review"
    assert "не найден в исходном тексте" in result.criterion_scores[0].explanation

def test_llm_invalid_criterion_id(mock_criteria):
    llm_result = EvaluationResult(
        total_score=1,
        criterion_scores=[
            CriterionScoreResult(
                criterion_id="fake_criterion",
                score=1,
                evidence_fragment="ответ",
                explanation="Объяснение",
                status="pre_confirmed",
                used_version_link="v1.0"
            )
        ],
        overall_status="success",
        version_id="v1.0",
        review_reason=None
    )
    engine = EvaluationEngine(llm_client=MockLLMClient(mock_result=llm_result))
    result = engine.evaluate_answer("Мой ответ", mock_criteria, "ЕГЭ", 2026, "task_1")
    assert result.overall_status == "needs_manual_review"
    assert result.criterion_scores[0].status == "needs_review"
    assert "применила несуществующий критерий" in result.criterion_scores[0].explanation

def test_llm_invalid_score(mock_criteria):
    llm_result = EvaluationResult(
        total_score=5,
        criterion_scores=[
            CriterionScoreResult(
                criterion_id="k1",
                score=5,
                evidence_fragment="ответ",
                explanation="Объяснение",
                status="pre_confirmed",
                used_version_link="v1.0"
            )
        ],
        overall_status="success",
        version_id="v1.0",
        review_reason=None
    )
    engine = EvaluationEngine(llm_client=MockLLMClient(mock_result=llm_result))
    result = engine.evaluate_answer("Мой ответ", mock_criteria, "ЕГЭ", 2026, "task_1")
    assert result.overall_status == "needs_manual_review"
    assert result.criterion_scores[0].status == "needs_review"
    assert "недопустимый балл" in result.criterion_scores[0].explanation

def test_successful_evaluation(mock_criteria):
    llm_result = EvaluationResult(
        total_score=2,
        criterion_scores=[
            CriterionScoreResult(
                criterion_id="k1",
                score=2,
                evidence_fragment="правильный ответ",
                explanation="Все верно",
                status="pre_confirmed",
                used_version_link="v1.0"
            )
        ],
        overall_status="success",
        version_id="v1.0",
        review_reason=None
    )
    engine = EvaluationEngine(llm_client=MockLLMClient(mock_result=llm_result))
    result = engine.evaluate_answer("Это правильный ответ на задание", mock_criteria, "ЕГЭ", 2026, "task_1")
    assert result.overall_status == "success"
    assert result.criterion_scores[0].status == "pre_confirmed"
