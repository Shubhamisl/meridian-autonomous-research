import pytest

from src.meridian.application.pipeline.relevance_scorer import RelevanceAssessment, RelevanceScorer
from src.meridian.application.pipeline.reliability_policy import ReliabilityPolicy
from src.meridian.domain.entities import Document


class FakeResponse:
    def __init__(self, content: str):
        self.content = content


class FakeOpenRouterClient:
    def __init__(self, response_texts=None, exc: Exception | None = None):
        self.response_texts = list(response_texts or [])
        self.exc = exc
        self.calls = 0
        self.last_messages = None

    async def generate_response(self, messages):
        self.calls += 1
        self.last_messages = messages
        if self.exc is not None:
            raise self.exc
        content = self.response_texts[min(self.calls - 1, len(self.response_texts) - 1)]
        return FakeResponse(content)


@pytest.mark.asyncio
async def test_score_rejects_obvious_topic_mismatch_without_llm():
    scorer = RelevanceScorer(policy=ReliabilityPolicy())
    document = Document(
        source="arxiv",
        url="https://example.com/solar",
        title="Solar Upper Transition Region Imager",
        content="Solar imaging payload for atmospheric observation.",
    )

    assessment = await scorer.score("mRNA vaccine advances", document)

    assert assessment.score < scorer.policy.relevance.auto_reject_below
    assert assessment.reason == "lexical_mismatch"
    assert assessment.llm_attempted is False


@pytest.mark.asyncio
async def test_score_uses_llm_for_borderline_candidates():
    client = FakeOpenRouterClient(['{"score": 0.82, "reason": "relevant"}'])
    scorer = RelevanceScorer(openrouter_client=client, policy=ReliabilityPolicy())
    document = Document(
        source="pubmed",
        url="https://example.com/gene",
        title="Gene therapy review",
        content="A review of related therapies.",
    )

    assessment = await scorer.score("gene therapy crispr", document)

    assert assessment.score == 0.82
    assert assessment.reason == "llm_adjudicated"
    assert assessment.llm_attempted is True
    assert assessment.llm_success is True
    assert client.calls == 1
    assert client.last_messages[0]["role"] == "system"


@pytest.mark.asyncio
async def test_score_falls_back_deterministically_when_llm_is_missing_or_bad():
    client = FakeOpenRouterClient(["not json"])
    scorer = RelevanceScorer(openrouter_client=client, policy=ReliabilityPolicy())
    document = Document(
        source="pubmed",
        url="https://example.com/gene",
        title="Gene therapy review",
        content="A review of related therapies.",
    )

    assessment = await scorer.score("gene therapy crispr", document)

    assert assessment.reason == "borderline_fallback"
    assert assessment.llm_attempted is True
    assert assessment.llm_success is False
    assert assessment.score < scorer.policy.relevance.borderline_below
    assert client.calls == 1
