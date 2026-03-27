import sys
import types
import math

import pytest

from src.meridian.domain.entities import Chunk

chromadb_stub = types.ModuleType("chromadb")
chromadb_stub.PersistentClient = lambda path: None
sys.modules.setdefault("chromadb", chromadb_stub)

from src.meridian.infrastructure.vector_store.chroma_repository import ChromaChunkRepository


class FakeCollection:
    def __init__(self, query_result=None):
        self.upsert_args = None
        self.query_result = query_result

    def upsert(self, **kwargs):
        self.upsert_args = kwargs

    def query(self, **kwargs):
        if self.query_result is not None:
            return self.query_result
        metadata = self.upsert_args["metadatas"][0]
        return {
            "ids": [[self.upsert_args["ids"][0]]],
            "documents": [[self.upsert_args["documents"][0]]],
            "metadatas": [[metadata]],
        }


class FakeClient:
    def __init__(self, collection):
        self.collection = collection

    def get_or_create_collection(self, name):
        return self.collection


@pytest.mark.asyncio
async def test_chunk_credibility_score_survives_chroma_round_trip(monkeypatch):
    collection = FakeCollection()
    monkeypatch.setattr("src.meridian.infrastructure.vector_store.chroma_repository.chromadb.PersistentClient", lambda path: FakeClient(collection))

    repository = ChromaChunkRepository(persist_directory="./ignored")
    original = Chunk(
        id="chunk-1",
        document_id="doc-1",
        content="Example chunk",
        metadata={"document_id": "doc-1"},
        credibility_score=0.87,
    )

    await repository.save_all("job-1", [original])
    restored = await repository.search("job-1", "example", top_k=1)

    assert collection.upsert_args["metadatas"][0]["credibility_score"] == 0.87
    assert restored[0].credibility_score == 0.87


@pytest.mark.asyncio
async def test_search_reranks_by_weighted_similarity_and_credibility(monkeypatch):
    collection = FakeCollection(
        query_result={
            "ids": [["chunk-1", "chunk-2", "chunk-3"]],
            "documents": [["first", "second", "third"]],
            "metadatas": [[
                {"document_id": "doc-1", "credibility_score": 0.1},
                {"document_id": "doc-2", "credibility_score": 1.0},
                {"document_id": "doc-3", "credibility_score": 0.0},
            ]],
            "distances": [[0.1, 0.3, 0.05]],
        }
    )
    monkeypatch.setattr("src.meridian.infrastructure.vector_store.chroma_repository.chromadb.PersistentClient", lambda path: FakeClient(collection))

    repository = ChromaChunkRepository(persist_directory="./ignored")

    results = await repository.search("job-1", "example", top_k=3)

    assert [chunk.id for chunk in results] == ["chunk-2", "chunk-3", "chunk-1"]
    assert [chunk.content for chunk in results] == ["second", "third", "first"]
    assert [chunk.credibility_score for chunk in results] == [1.0, 0.0, 0.1]


@pytest.mark.asyncio
async def test_search_defaults_missing_credibility_score_to_half(monkeypatch):
    collection = FakeCollection(
        query_result={
            "ids": [["chunk-b", "chunk-a"]],
            "documents": [["second", "first"]],
            "metadatas": [[
                {"document_id": "doc-b", "credibility_score": 0.1},
                {"document_id": "doc-a"},
            ]],
            "distances": [[0.2, 0.2]],
        }
    )
    monkeypatch.setattr("src.meridian.infrastructure.vector_store.chroma_repository.chromadb.PersistentClient", lambda path: FakeClient(collection))

    repository = ChromaChunkRepository(persist_directory="./ignored")

    results = await repository.search("job-2", "example", top_k=2)

    assert [chunk.id for chunk in results] == ["chunk-a", "chunk-b"]
    assert results[0].credibility_score == 0.5
    assert results[1].credibility_score == 0.1


@pytest.mark.asyncio
async def test_search_falls_back_to_default_weights_for_invalid_env_values(monkeypatch):
    monkeypatch.setenv("SIMILARITY_WEIGHT", "not-a-number")
    monkeypatch.setenv("CREDIBILITY_WEIGHT", "still-not-a-number")

    collection = FakeCollection(
        query_result={
            "ids": [["chunk-a", "chunk-b"]],
            "documents": [["first", "second"]],
            "metadatas": [[
                {"document_id": "doc-a", "credibility_score": 0.0},
                {"document_id": "doc-b", "credibility_score": 1.0},
            ]],
            "distances": [[0.1, 0.0]],
        }
    )
    monkeypatch.setattr("src.meridian.infrastructure.vector_store.chroma_repository.chromadb.PersistentClient", lambda path: FakeClient(collection))

    repository = ChromaChunkRepository(persist_directory="./ignored")

    results = await repository.search("job-3", "example", top_k=2)

    assert [chunk.id for chunk in results] == ["chunk-b", "chunk-a"]
    assert [chunk.credibility_score for chunk in results] == [1.0, 0.0]


def test_get_weight_rejects_non_finite_env_values(monkeypatch):
    monkeypatch.setenv("SIMILARITY_WEIGHT", "NaN")
    monkeypatch.setenv("CREDIBILITY_WEIGHT", "inf")

    monkeypatch.setattr("src.meridian.infrastructure.vector_store.chroma_repository.chromadb.PersistentClient", lambda path: FakeClient(FakeCollection()))
    repository = ChromaChunkRepository(persist_directory="./ignored")

    assert repository._get_weight("SIMILARITY_WEIGHT", 0.7) == 0.7
    assert repository._get_weight("CREDIBILITY_WEIGHT", 0.3) == 0.3
    assert math.isfinite(repository._get_weight("SIMILARITY_WEIGHT", 0.7))
    assert math.isfinite(repository._get_weight("CREDIBILITY_WEIGHT", 0.3))
