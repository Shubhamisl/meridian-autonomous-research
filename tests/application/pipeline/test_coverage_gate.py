from src.meridian.application.pipeline.coverage_gate import CoverageGate
from src.meridian.application.pipeline.reliability_policy import ReliabilityPolicy


def test_biomedical_coverage_requires_three_documents_and_two_sources():
    gate = CoverageGate(ReliabilityPolicy())

    verdict = gate.evaluate(
        domain="biomedical",
        accepted_count=2,
        distinct_sources=2,
        average_relevance=0.80,
    )

    assert verdict.action == "retry"
    assert verdict.reason == "insufficient_documents"
    assert verdict.required_documents == 3
    assert verdict.required_sources == 2


def test_general_coverage_passes_with_two_documents_and_one_source():
    gate = CoverageGate(ReliabilityPolicy())

    verdict = gate.evaluate(
        domain="general",
        accepted_count=2,
        distinct_sources=1,
        average_relevance=0.70,
    )

    assert verdict.action == "synthesize"
    assert verdict.reason == "sufficient_coverage"


def test_coverage_gate_reports_relevance_shortfall():
    gate = CoverageGate(ReliabilityPolicy())

    verdict = gate.evaluate(
        domain="legal",
        accepted_count=3,
        distinct_sources=2,
        average_relevance=0.60,
    )

    assert verdict.action == "retry"
    assert verdict.reason == "insufficient_relevance"
    assert verdict.required_average_relevance == 0.70
