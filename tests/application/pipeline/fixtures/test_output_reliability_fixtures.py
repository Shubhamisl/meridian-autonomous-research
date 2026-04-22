import pytest

from src.meridian.application.pipeline.coverage_gate import CoverageGate
from src.meridian.application.pipeline.evidence_selection import EvidenceSelectionService
from src.meridian.application.pipeline.relevance_scorer import RelevanceScorer
from src.meridian.application.pipeline.reliability_policy import ReliabilityPolicy
from src.meridian.domain.entities import Document


FIXTURES = [
    {
        "name": "biomedical_mrna_noise_rejection",
        "query": "Recent advances in mRNA vaccines",
        "expected_domain": "biomedical",
        "documents": [
            Document(
                source="pubmed",
                url="https://example.com/pubmed-1",
                title="Recent advances in mRNA vaccines",
                content="Recent advances in mRNA vaccines improve delivery platforms and efficacy.",
            ),
            Document(
                source="arxiv",
                url="https://example.com/arxiv-1",
                title="mRNA vaccines advances in immunotherapy",
                content="Recent advances in mRNA vaccines and immunotherapy are discussed.",
            ),
            Document(
                source="wikipedia",
                url="https://example.com/wiki-1",
                title="mRNA vaccines",
                content="Recent advances in mRNA vaccines are summarized for a broad audience.",
            ),
            Document(
                source="arxiv",
                url="https://example.com/arxiv-solar",
                title="Solar Upper Transition Region Imager",
                content="Solar imaging payload for atmospheric observation.",
            ),
        ],
        "source_queries": {
            "pubmed": ["Recent advances in mRNA vaccines"],
            "arxiv": ['"mRNA vaccines"'],
            "wikipedia": ["mRNA vaccines"],
        },
        "accept_titles": [
            "Recent advances in mRNA vaccines",
            "mRNA vaccines advances in immunotherapy",
            "mRNA vaccines",
        ],
        "reject_titles": ["Solar Upper Transition Region Imager"],
        "expected_coverage_action": "synthesize",
        "expect_retry": False,
        "expect_synthesis": True,
    },
    {
        "name": "general_ai_regulation_filters_off_topic_noise",
        "query": "AI regulation in EU",
        "expected_domain": "general",
        "documents": [
            Document(
                source="semantic_scholar",
                url="https://example.com/ss-1",
                title="AI regulation in EU markets",
                content="AI regulation in EU markets affects competition and governance.",
            ),
            Document(
                source="web",
                url="https://example.com/web-1",
                title="EU AI Act overview",
                content="AI regulation in EU law and governance continues to evolve.",
            ),
            Document(
                source="arxiv",
                url="https://example.com/arxiv-solar-2",
                title="Solar imaging payload",
                content="Observations of the sun and atmospheric effects.",
            ),
        ],
        "source_queries": {
            "semantic_scholar": ["AI regulation in EU"],
            "web": ["AI regulation in EU -site:reddit.com -site:quora.com"],
            "arxiv": ['"AI regulation in EU"'],
        },
        "accept_titles": [
            "AI regulation in EU markets",
            "EU AI Act overview",
        ],
        "reject_titles": ["Solar imaging payload"],
        "expected_coverage_action": "synthesize",
        "expect_retry": False,
        "expect_synthesis": True,
    },
]


@pytest.mark.parametrize("fixture", FIXTURES, ids=[fixture["name"] for fixture in FIXTURES])
@pytest.mark.asyncio
async def test_output_reliability_fixtures_match_expected_accept_reject_and_coverage(fixture):
    policy = ReliabilityPolicy()
    scorer = RelevanceScorer(policy=policy)
    service = EvidenceSelectionService(policy=policy, relevance_scorer=scorer)
    coverage_gate = CoverageGate(policy)

    selection = await service.select(
        query=fixture["query"],
        domain=fixture["expected_domain"],
        candidates=fixture["documents"],
        source_queries=fixture["source_queries"],
    )

    accepted_titles = [decision.document.title for decision in selection.accepted]
    rejected_titles = [decision.document.title for decision in selection.rejected]
    average_relevance = (
        sum(decision.relevance_score for decision in selection.accepted) / len(selection.accepted)
        if selection.accepted
        else 0.0
    )
    verdict = coverage_gate.evaluate(
        domain=fixture["expected_domain"],
        accepted_count=len(selection.accepted),
        distinct_sources=len({decision.document.source for decision in selection.accepted}),
        average_relevance=average_relevance,
        source_distribution={
            source: sum(1 for decision in selection.accepted if decision.document.source == source)
            for source in {decision.document.source for decision in selection.accepted}
        },
        query_family_distribution={
            f"{decision.document.source}::{decision.source_query or 'unknown_query'}": sum(
                1
                for candidate in selection.accepted
                if candidate.document.source == decision.document.source
                and candidate.source_query == decision.source_query
            )
            for decision in selection.accepted
        },
    )

    assert accepted_titles == fixture["accept_titles"]
    assert rejected_titles == fixture["reject_titles"]
    assert verdict.action == fixture["expected_coverage_action"]
    assert (verdict.action == "retry") is fixture["expect_retry"]
    assert (verdict.action == "synthesize") is fixture["expect_synthesis"]
