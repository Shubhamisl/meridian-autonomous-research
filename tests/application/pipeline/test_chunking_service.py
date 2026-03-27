import pytest

from src.meridian.application.pipeline.chunking import ChunkingService
from src.meridian.domain.entities import Document


class FakeCredibilityScorer:
    def __init__(self, scores):
        self.scores = list(scores)
        self.calls = []

    async def score(self, document):
        self.calls.append(document.id)
        return self.scores[min(len(self.calls) - 1, len(self.scores) - 1)]


@pytest.mark.asyncio
async def test_chunk_documents_applies_one_score_to_every_chunk_from_a_document():
    document = Document(
        source="web",
        url="https://example.com/article",
        title="Long article",
        content="a" * 1700,
    )
    scorer = FakeCredibilityScorer([0.73])
    service = ChunkingService(scorer)

    chunks = await service.chunk_documents([document])

    assert len(chunks) > 1
    assert scorer.calls == [document.id]
    assert all(chunk.document_id == document.id for chunk in chunks)
    assert [chunk.credibility_score for chunk in chunks] == [0.73] * len(chunks)


@pytest.mark.asyncio
async def test_chunk_documents_keeps_chunks_when_score_is_neutral_fallback():
    document = Document(
        source="web",
        url="https://example.com/article",
        title="Long article",
        content="b" * 1700,
    )
    scorer = FakeCredibilityScorer([0.5])
    service = ChunkingService(scorer)

    chunks = await service.chunk_documents([document])

    assert chunks
    assert [chunk.credibility_score for chunk in chunks] == [0.5] * len(chunks)
