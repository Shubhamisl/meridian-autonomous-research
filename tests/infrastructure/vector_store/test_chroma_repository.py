import sys
import types

import pytest

from src.meridian.domain.entities import Chunk

chromadb_stub = types.ModuleType("chromadb")
chromadb_stub.PersistentClient = lambda path: None
sys.modules.setdefault("chromadb", chromadb_stub)

from src.meridian.infrastructure.vector_store.chroma_repository import ChromaChunkRepository


class FakeCollection:
    def __init__(self):
        self.upsert_args = None

    def upsert(self, **kwargs):
        self.upsert_args = kwargs

    def query(self, **kwargs):
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
