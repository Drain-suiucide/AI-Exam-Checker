import json
import pytest
from datetime import date
import os
from app.schemas.evaluation import CriteriaVersion, CriterionDetails, ScoreVariant, EvaluationResult
from app.services.evaluation.engine import EvaluationEngine

class MockLLMClient:
    def __init__(self, mock_result_dict):
        # Парсим словарь обратно в Pydantic схему, чтобы сымитировать валидный ответ модели
        self.mock_result = EvaluationResult(**mock_result_dict)

    def generate(self, student_answer, criteria, system_prompt):
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
                official_description="Исторические факты",
                llm_instruction="Оцени наличие фактов",
                project_rules="",
                diagnostic_hints="",
                score_variants=[ScoreVariant(score=0, condition="Нет"), ScoreVariant(score=1, condition="Частично"), ScoreVariant(score=2, condition="Да")],
                required_evidence="Цитата из текста с фактом",
                ambiguity_rules="На ревью при сомнениях"
            )
        ]
    )

def test_synthetic_cases(mock_criteria):
    json_path = os.path.join(os.path.dirname(__file__), 'synthetic_cases.json')
    with open(json_path, 'r', encoding='utf-8') as f:
        cases = json.load(f)

    for case in cases:
        print(f"Running case: {case['case_id']} - {case['description']}")
        engine = EvaluationEngine(llm_client=MockLLMClient(case['mock_llm_response']))
        result = engine.evaluate_answer(
            student_answer=case['student_answer'],
            criteria=mock_criteria,
            exam="ЕГЭ",
            year=2026,
            task_id="task_1"
        )
        
        assert result.overall_status == case['expected_overall_status'], \
            f"Failed on {case['case_id']}: expected status {case['expected_overall_status']}, got {result.overall_status}"
            
        if 'expected_review_reason' in case:
            assert result.review_reason is not None
            assert case['expected_review_reason'] in result.review_reason, \
                f"Failed on {case['case_id']}: expected reason to contain '{case['expected_review_reason']}', got '{result.review_reason}'"
