import chromadb
from typing import List
from src.meridian.domain.entities import Chunk
from src.meridian.domain.repositories import ChunkRepository

class ChromaChunkRepository(ChunkRepository):
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(name="chunks")

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
        
        chunks = []
        if results and results["ids"] and len(results["ids"]) > 0:
            for idx in range(len(results["ids"][0])):
                metadata = results["metadatas"][0][idx]
                chunks.append(Chunk(
                    id=results["ids"][0][idx],
                    document_id=metadata.get("document_id", "unknown"),
                    content=results["documents"][0][idx],
                    metadata=metadata,
                    credibility_score=metadata.get("credibility_score", 0.5)
                ))
        return chunks
