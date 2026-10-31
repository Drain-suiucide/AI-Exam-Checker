import io
from datetime import date
from PIL import Image
import pytest

from app.schemas.evaluation import (
    CriteriaVersion,
    CriterionDetails,
    CriterionScoreResult,
    EvaluationResult,
    ScoreVariant,
)
from app.services.evaluation.engine import EvaluationEngine
from app.services.ocr.mock_engine import MockEngine
from app.services.ocr.pipeline import OcrPipeline


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
                    ScoreVariant(score=2, condition="Да"),
                ],
                required_evidence="Цитата из текста с фактом",
                ambiguity_rules="На ревью при сомнениях",
            )
        ],
    )


def test_scenario_b_image_ocr_edit_evaluate(mock_criteria):
    """
    Сценарий B:
    1. Пользователь загружает допустимое изображение
    2. OCR возвращает распознанный текст (с опечаткой)
    3. Пользователь исправляет текст в UI/клиенте
    4. Запускается оценивание исправленного текста
    """
    # 1. Допустимое изображение
    buf = io.BytesIO()
    img = Image.new("RGB", (200, 100), (255, 255, 255))
    img.save(buf, format="PNG")
    raw_bytes = buf.getvalue()

    # 2. OCR распознает (например, с опечаткой 'крепосная')
    mock_engine = MockEngine(text="В 1861 году была отменена крепосная зависимость.")
    pipeline = OcrPipeline(engine=mock_engine)
    ocr_result = pipeline.recognize([raw_bytes])
    assert "крепосная" in ocr_result.text

    # 3. Пользователь правит текст
    user_corrected_text = (
        ocr_result.text.replace("крепосная", "крепостная")
        + " Манифест подписал Александр II."
    )

    # 4. Запуск оценивания исправленного текста
    class CorrectedLLM:
        def generate(self, answer, criteria, prompt):
            return EvaluationResult(
                total_score=2,
                criterion_scores=[
                    CriterionScoreResult(
                        criterion_id="k1",
                        score=2,
                        evidence_fragment="отменена крепостная зависимость",
                        explanation="Верно указан факт и формулировка",
                        status="pre_confirmed",
                        used_version_link="v1.0",
                    )
                ],
                overall_status="success",
                version_id="v1.0",
            )

    eval_engine = EvaluationEngine(llm_client=CorrectedLLM())
    eval_res = eval_engine.evaluate_answer(
        student_answer=user_corrected_text,
        criteria=mock_criteria,
        exam="ЕГЭ",
        year=2026,
        task_id="task_1",
    )
    assert eval_res.overall_status == "success"
    assert eval_res.total_score == 2
