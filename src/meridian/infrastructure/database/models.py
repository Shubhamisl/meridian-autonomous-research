from sqlalchemy import Column, String, Text, DateTime, MetaData
from sqlalchemy.orm import declarative_base

metadata = MetaData()
Base = declarative_base(metadata=metadata)

class DBResearchJob(Base):
    __tablename__ = 'research_jobs'

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=True)
    query = Column(String, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    workspace_metadata = Column(Text, nullable=True)

class DBResearchReport(Base):
    __tablename__ = 'research_reports'

    id = Column(String, primary_key=True)
    job_id = Column(String, nullable=False)
    query = Column(String, nullable=False)
    markdown_content = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False)
    workspace_metadata = Column(Text, nullable=True)
