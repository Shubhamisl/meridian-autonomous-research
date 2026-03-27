import pytest

from src.meridian.application.pipeline.credibility_scorer import CredibilityScorer
from src.meridian.domain.entities import Document


class FakeResponse:
    def __init__(self, content: str):
        self.content = content


class FakeOpenRouterClient:
    def __init__(self, response_texts=None):
        self.response_texts = list(response_texts or [])
        self.last_messages = None
        self.calls = 0

    async def generate_response(self, messages):
        self.last_messages = messages
        self.calls += 1
        content = self.response_texts[min(self.calls - 1, len(self.response_texts) - 1)]
        return FakeResponse(content)


@pytest.mark.asyncio
async def test_score_returns_heuristic_for_non_web_sources():
    client = FakeOpenRouterClient(['{"score": 1.0, "reason": "ignored"}'])
    scorer = CredibilityScorer(client)
    document = Document(source="pubmed", url="https://example.com", title="T", content="C")

    result = await scorer.score(document)

    assert result == 0.92
    assert client.calls == 0


@pytest.mark.asyncio
async def test_score_uses_llm_for_web_sources_with_valid_json_payload():
    client = FakeOpenRouterClient(['{"score": 0.73, "reason": "credible"}'])
    scorer = CredibilityScorer(client)
    document = Document(source="web", url="https://example.com", title="T", content="C")

    result = await scorer.score(document)

    assert result == 0.73
    assert client.calls == 1
    assert client.last_messages[0]["role"] == "system"
    assert "strict json" in client.last_messages[0]["content"].lower()


@pytest.mark.asyncio
async def test_score_returns_zero_for_valid_web_payload_with_zero_score():
    client = FakeOpenRouterClient(['{"score": 0.0, "reason": "not credible"}'])
    scorer = CredibilityScorer(client)
    document = Document(source="web", url="https://example.com", title="T", content="C")

    result = await scorer.score(document)

    assert result == 0.0
    assert client.calls == 1


@pytest.mark.asyncio
async def test_score_falls_back_to_heuristic_for_invalid_web_payload():
    client = FakeOpenRouterClient(["not json"])
    scorer = CredibilityScorer(client)
    document = Document(source="web", url="https://example.com", title="T", content="C")

    result = await scorer.score(document)

    assert result == 0.4
    assert client.calls == 1


@pytest.mark.asyncio
async def test_score_stops_auditing_web_sources_after_cap():
    client = FakeOpenRouterClient(['{"score": 0.91, "reason": "audited"}'])
    scorer = CredibilityScorer(client, web_audit_limit=1)
    first = Document(source="web", url="https://example.com/1", title="T1", content="C1")
    second = Document(source="web", url="https://example.com/2", title="T2", content="C2")

    first_score = await scorer.score(first)
    second_score = await scorer.score(second)

    assert first_score == 0.91
    assert second_score == 0.4
    assert client.calls == 1
