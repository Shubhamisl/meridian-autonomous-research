import pytest

from src.meridian.application.pipeline.evidence_selection import EvidenceSelectionService
from src.meridian.application.pipeline.reliability_policy import ReliabilityPolicy
from src.meridian.domain.entities import Document


class FakeAssessment:
    def __init__(self, score: float, reason: str, llm_attempted: bool = False, llm_success: bool = False):
        self.score = score
        self.reason = reason
        self.llm_attempted = llm_attempted
        self.llm_success = llm_success


class FakeRelevanceScorer:
    def __init__(self, assessments: dict[tuple[str, str], FakeAssessment]):
        self.assessments = assessments
        self.calls = []

    async def score(self, query: str, document: Document):
        self.calls.append((query, document.title, document.url))
        return self.assessments[(document.title, document.url)]


@pytest.mark.asyncio
async def test_select_rejects_obvious_mismatch_with_reason():
    service = EvidenceSelectionService(policy=ReliabilityPolicy())
    candidates = [
        Document(
            source="arxiv",
            url="https://example.com/solar",
            title="Solar Upper Transition Region Imager",
            content="Solar imaging payload for atmospheric observation.",
        )
    ]

    result = await service.select(
        query="mRNA vaccine advances",
        domain="biomedical",
        candidates=candidates,
        source_queries={"arxiv": "mRNA vaccine advances"},
    )

    assert len(result.accepted) == 0
    assert len(result.rejected) == 1
    assert result.rejected[0].reason == "low_relevance"
    assert result.rejected[0].relevance_score < service.policy.relevance.auto_reject_below


@pytest.mark.asyncio
async def test_select_collapses_duplicates_before_scoring():
    document_one = Document(
        source="pubmed",
        url="https://example.com/mrna",
        title="mRNA vaccine advances",
        content="Advances in vaccine delivery and trial design.",
    )
    document_two = Document(
        source="pubmed",
        url="https://example.com/mrna",
        title="mRNA vaccine advances",
        content="Advances in vaccine delivery and trial design.",
    )
    scorer = FakeRelevanceScorer(
        {
            (document_one.title, document_one.url): FakeAssessment(0.83, "accepted"),
        }
    )
    service = EvidenceSelectionService(policy=ReliabilityPolicy(), relevance_scorer=scorer)

    result = await service.select(
        query="mRNA vaccine advances",
        domain="biomedical",
        candidates=[document_one, document_two],
        source_queries={"pubmed": "mRNA vaccine advances"},
    )

    assert len(result.accepted) == 1
    assert len(result.rejected) == 1
    assert result.accepted[0].document == document_one
    assert result.rejected[0].reason == "duplicate"
    assert result.rejected[0].relevance_score == 0.83
    assert len(scorer.calls) == 1
