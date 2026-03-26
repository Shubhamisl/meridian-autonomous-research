from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from uuid import uuid4

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
    status: str = "pending" # pending, running, completed, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    def start(self) -> "ResearchJob":
        return self.copy(update={"status": "running"})

    def complete(self) -> "ResearchJob":
        return self.copy(update={"status": "completed", "completed_at": datetime.utcnow()})

    def fail(self, error_message: str) -> "ResearchJob":
        return self.copy(update={"status": "failed", "completed_at": datetime.utcnow(), "error_message": error_message})
