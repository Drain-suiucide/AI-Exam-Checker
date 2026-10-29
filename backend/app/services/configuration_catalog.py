"""Configuration catalogue provider.

The demo provider is deliberately explicit: until the official subject data is
approved, the API must not invent a live exam task or scoring criteria.
"""

from datetime import UTC, datetime

from app.schemas.configurations import (
    Aggregation,
    ConfigurationLimits,
    CriteriaInfo,
    Criterion,
    CriterionLevel,
    EvaluationProfileInfo,
    ExamConfigurationResponse,
    ExamInfo,
    Material,
    SourceInfo,
    TaskInfo,
)


def demo_configurations() -> list[ExamConfigurationResponse]:
    """Return the stable synthetic configuration used by local demo mode."""
    now = datetime.now(UTC)
    return [
        ExamConfigurationResponse(
            id="00000000-0000-4000-8000-000000000001",
            slug="ege-history-demo",
            status="draft",
            is_default=True,
            exam=ExamInfo(
                code="ege-history",
                subject="history",
                title="ЕГЭ по истории",
                version_label="demo",
                exam_year=2026,
            ),
            task=TaskInfo(
                task_version_id="00000000-0000-4000-8000-000000000002",
                task_key="history-concept-and-fact",
                task_number="19",
                version=1,
                title="Историческое понятие и факт",
                statement=(
                    "Раскройте смысл исторического понятия и приведите "
                    "один конкретный исторический факт."
                ),
                materials=[
                    Material(kind="text", title="Условие", content="Синтетическое demo-условие")
                ],
                max_score=2,
            ),
            criteria_version=CriteriaInfo(
                id="00000000-0000-4000-8000-000000000003",
                version=1,
                aggregation=Aggregation(type="sum"),
                max_score_total=2,
                criteria=[
                    Criterion(
                        id="00000000-0000-4000-8000-000000000004",
                        code="K1",
                        position=1,
                        title="Смысл понятия",
                        description="Понятие раскрыто корректно.",
                        max_score=1,
                        levels=[
                            CriterionLevel(score=0, description="Не раскрыто"),
                            CriterionLevel(score=1, description="Раскрыто"),
                        ],
                    ),
                    Criterion(
                        id="00000000-0000-4000-8000-000000000005",
                        code="K2",
                        position=2,
                        title="Конкретный факт",
                        description="Приведён конкретный исторический факт.",
                        max_score=1,
                        levels=[
                            CriterionLevel(score=0, description="Не приведён"),
                            CriterionLevel(score=1, description="Приведён"),
                        ],
                    ),
                ],
            ),
            evaluation_profile=EvaluationProfileInfo(
                id="00000000-0000-4000-8000-000000000006",
                code="demo-history-v1",
                version=1,
                model_provider="mock",
                model_name="demo",
            ),
            sources=[
                SourceInfo(
                    publisher="AI Exam Checker",
                    title="Synthetic demo data",
                    edition_label="v1",
                    url=None,
                    retrieved_at=now,
                )
            ],
            limits=ConfigurationLimits(
                max_files=4,
                max_file_bytes=8 * 1024 * 1024,
                allowed_mime_types=["image/jpeg", "image/png", "image/webp"],
                min_answer_chars=10,
                max_answer_chars=10_000,
            ),
            created_at=now,
            approved_at=None,
        )
    ]
