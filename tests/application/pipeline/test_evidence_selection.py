import pytest

from src.meridian.application.pipeline.evidence_selection import EvidenceSelectionService
from src.meridian.application.pipeline.reliability_policy import ReliabilityPolicy
from src.meridian.domain.entities import Document


class FakeAssessment:
    def __init__(
        self,
        score: float,
        reason: str,
        llm_attempted: bool = False,
        llm_success: bool = False,
        detail: str | None = None,
    ):
        self.score = score
        self.reason = reason
        self.llm_attempted = llm_attempted
        self.llm_success = llm_success
        self.detail = detail


class FakeRelevanceScorer:
    def __init__(self, assessments: dict[tuple[str, str], FakeAssessment]):
        self.assessments = assessments
        self.calls = []

    async def score(self, query: str, document: Document, llm_budget_remaining: int | None = None):
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


@pytest.mark.asyncio
async def test_select_preserves_provenance_and_scorer_detail():
    document = Document(
        source="semantic_scholar",
        url="https://example.com/ai-eu",
        title="AI regulation in the EU",
        content="A discussion of AI governance.",
    )
    scorer = FakeRelevanceScorer(
        {
            (document.title, document.url): FakeAssessment(
                0.78,
                "llm_adjudicated",
                llm_attempted=True,
                llm_success=True,
                detail="aligned with query terms",
            ),
        }
    )
    service = EvidenceSelectionService(policy=ReliabilityPolicy(), relevance_scorer=scorer)

    result = await service.select(
        query="AI regulation in EU",
        domain="general",
        candidates=[document],
        source_queries={"semantic_scholar": "AI regulation in EU"},
    )

    assert len(result.accepted) == 1
    decision = result.accepted[0]
    assert decision.reason == "accepted"
    assert decision.scorer_reason == "llm_adjudicated"
    assert decision.scorer_detail == "aligned with query terms"
    assert decision.source_query == "AI regulation in EU"
    assert decision.adjudication_detail == "aligned with query terms"
    assert result.source_queries["semantic_scholar"] == ["AI regulation in EU"]
