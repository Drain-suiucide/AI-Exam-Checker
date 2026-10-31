from pathlib import Path
from app.services.evaluation.evaluate_quality import run_evaluation_quality_suite

def test_evaluation_quality_suite():
    benchmark_file = (
        Path(__file__).resolve().parent / "independent_benchmark.json"
    )
    assert benchmark_file.exists()
    metrics = run_evaluation_quality_suite(benchmark_file)
    assert metrics.total_cases == 12
    assert metrics.agreement_rate >= 0.95
    assert metrics.exact_score_match_rate >= 0.95
    assert metrics.k1_accuracy >= 0.95
    assert metrics.k2_accuracy >= 0.95
    assert metrics.escalation_rate > 0.10  # Must escalate ambiguous cases!
