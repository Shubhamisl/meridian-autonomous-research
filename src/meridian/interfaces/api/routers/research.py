from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.meridian.infrastructure.database.session import engine, async_sessionmaker
from src.meridian.infrastructure.database.models import DBResearchJob, DBResearchReport
from src.meridian.domain.entities import ResearchJob
from src.meridian.infrastructure.database.sqlite_repositories import SQLiteResearchJobRepository, SQLiteResearchReportRepository
from src.meridian.infrastructure.auth.firebase_auth import get_current_user
from src.meridian.interfaces.workers.tasks import run_research_pipeline
import logging

router = APIRouter()
SessionLocal = async_sessionmaker(bind=engine, autoflush=False, autocommit=False)

async def get_db():
    async with SessionLocal() as session:
        yield session

class ResearchRequest(BaseModel):
    query: str

class ResearchResponse(BaseModel):
    id: str
    status: str

@router.post("/", response_model=ResearchResponse)
async def create_research(
    request: ResearchRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    job_repo = SQLiteResearchJobRepository(db)
    job = ResearchJob(query=request.query, user_id=user["uid"])
    
    await job_repo.save(job)
    
    try:
         run_research_pipeline.delay(job.id)
    except Exception as e:
         logging.error(f"Failed to queue task: {e}")
         job = job.fail(error_message=str(e))
         await job_repo.save(job)
         
    return ResearchResponse(id=job.id, status=job.status)

@router.get("/", response_model=list[ResearchResponse])
async def list_user_research(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """List all research jobs for the authenticated user."""
    result = await db.execute(
        select(DBResearchJob)
        .where(DBResearchJob.user_id == user["uid"])
        .order_by(DBResearchJob.created_at.desc())
    )
    jobs = result.scalars().all()
    return [ResearchResponse(id=j.id, status=j.status) for j in jobs]

@router.get("/{job_id}", response_model=ResearchResponse)
async def get_research_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    job_repo = SQLiteResearchJobRepository(db)
    job = await job_repo.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    return ResearchResponse(id=job.id, status=job.status)

@router.get("/{job_id}/report")
async def get_research_report(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    report_repo = SQLiteResearchReportRepository(db)
    report = await report_repo.get_by_job_id(job_id)
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not ready yet or job failed.")
        
    return {"id": report.id, "job_id": report.job_id, "query": report.query, "markdown_content": report.markdown_content}
