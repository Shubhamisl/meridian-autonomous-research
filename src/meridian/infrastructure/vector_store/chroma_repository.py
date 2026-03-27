import os
from typing import List

import chromadb

from src.meridian.domain.entities import Chunk
from src.meridian.domain.repositories import ChunkRepository

class ChromaChunkRepository(ChunkRepository):
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(name="chunks")

    def _get_weight(self, env_name: str, default: float) -> float:
        raw_value = os.getenv(env_name)
        if raw_value is None:
            return default
        try:
            return float(raw_value)
        except (TypeError, ValueError):
            return default

    async def save_all(self, job_id: str, chunks: List[Chunk]) -> None:
        if not chunks:
            return
            
        self.collection.upsert(
            ids=[c.id for c in chunks],
            documents=[c.content for c in chunks],
            metadatas=[
                {**c.metadata, "job_id": job_id, "credibility_score": c.credibility_score}
                for c in chunks
            ]
        )

    async def search(self, job_id: str, query: str, top_k: int = 5) -> List[Chunk]:
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where={"job_id": job_id}
        )

        similarity_weight = self._get_weight("SIMILARITY_WEIGHT", 0.7)
        credibility_weight = self._get_weight("CREDIBILITY_WEIGHT", 0.3)

        ranked_chunks = []
        if results and results.get("ids") and len(results["ids"]) > 0:
            ids = results["ids"][0]
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]

            for idx in range(len(ids)):
                metadata = metadatas[idx]
                distance = distances[idx] if idx < len(distances) else 1.0
                similarity = 1 - distance
                credibility_score = metadata.get("credibility_score", 0.5)
                final_score = (
                    similarity_weight * similarity
                    + credibility_weight * credibility_score
                )
                ranked_chunks.append(
                    (
                        final_score,
                        Chunk(
                            id=ids[idx],
                            document_id=metadata.get("document_id", "unknown"),
                            content=documents[idx],
                            metadata=metadata,
                            credibility_score=credibility_score,
                        ),
                    )
                )

        ranked_chunks.sort(key=lambda item: item[0], reverse=True)
        return [chunk for _, chunk in ranked_chunks]
