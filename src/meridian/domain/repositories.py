from typing import List, Optional, Protocol
from .entities import ResearchJob, Document, Chunk, ResearchReport

class ResearchJobRepository(Protocol):
    async def get(self, job_id: str) -> Optional[ResearchJob]:
        ...
    
    async def save(self, job: ResearchJob) -> None:
        ...

class ResearchReportRepository(Protocol):
    async def get_by_job_id(self, job_id: str) -> Optional[ResearchReport]:
        ...
    
    async def save(self, report: ResearchReport) -> None:
        ...

class DocumentRepository(Protocol):
    async def save_all(self, job_id: str, documents: List[Document]) -> None:
        ...
    
    async def get_by_job_id(self, job_id: str) -> List[Document]:
        ...

class ChunkRepository(Protocol):
    async def save_all(self, job_id: str, chunks: List[Chunk]) -> None:
        ...
    
    async def search(self, job_id: str, query: str, top_k: int = 5) -> List[Chunk]:
        ...
