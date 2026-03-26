from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from uuid import uuid4


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class Chunk(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    document_id: str
    content: str
    metadata: dict = Field(default_factory=dict)

class Document(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    source: str
    url: str
    title: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ResearchReport(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    job_id: str
    query: str
    markdown_content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ResearchJob(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    query: str
    user_id: Optional[str] = None
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    def start(self) -> "ResearchJob":
        return self.copy(update={"status": JobStatus.RUNNING})

    def complete(self) -> "ResearchJob":
        return self.copy(update={"status": JobStatus.COMPLETED, "completed_at": datetime.utcnow()})

    def fail(self, error_message: str) -> "ResearchJob":
        return self.copy(update={"status": JobStatus.FAILED, "completed_at": datetime.utcnow(), "error_message": error_message})
