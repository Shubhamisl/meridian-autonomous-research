from src.meridian.application.pipeline.coverage_gate import CoverageGate
from src.meridian.application.pipeline.reliability_policy import ReliabilityPolicy


def test_biomedical_coverage_requires_three_documents_and_two_sources():
    gate = CoverageGate(ReliabilityPolicy())

    verdict = gate.evaluate(
        domain="biomedical",
        accepted_count=2,
        distinct_sources=2,
        average_relevance=0.80,
        source_distribution={"pubmed": 1, "arxiv": 1},
        query_family_distribution={"pubmed::q1": 1, "arxiv::q2": 1},
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
        source_distribution={"web": 2},
        query_family_distribution={"web::q1": 2},
    )

    assert verdict.action == "synthesize"
    assert verdict.reason == "sufficient_coverage"


def test_coverage_gate_reports_relevance_shortfall():
    gate = CoverageGate(ReliabilityPolicy())

    verdict = gate.evaluate(
        domain="legal",
        accepted_count=4,
        distinct_sources=2,
        average_relevance=0.60,
        source_distribution={"web": 2, "wikipedia": 2},
        query_family_distribution={"web::q1": 2, "wikipedia::q2": 2},
    )

    assert verdict.action == "retry"
    assert verdict.reason == "insufficient_relevance"
    assert verdict.required_average_relevance == 0.70


def test_coverage_gate_rejects_source_skew_even_when_counts_are_sufficient():
    gate = CoverageGate(ReliabilityPolicy())

    verdict = gate.evaluate(
        domain="biomedical",
        accepted_count=3,
        distinct_sources=2,
        average_relevance=0.85,
        source_distribution={"pubmed": 2, "arxiv": 1},
        query_family_distribution={"pubmed::q1": 2, "arxiv::q2": 1},
    )

    assert verdict.action == "retry"
    assert verdict.reason == "insufficient_source_balance"


def test_coverage_gate_rejects_overconcentrated_query_family():
    gate = CoverageGate(ReliabilityPolicy())

    verdict = gate.evaluate(
        domain="general",
        accepted_count=5,
        distinct_sources=2,
        average_relevance=0.9,
        source_distribution={"semantic_scholar": 3, "wikipedia": 2},
        query_family_distribution={"semantic_scholar::q1": 3, "wikipedia::q2": 2},
    )

    assert verdict.action == "retry"
    assert verdict.reason == "insufficient_query_family_diversity"
