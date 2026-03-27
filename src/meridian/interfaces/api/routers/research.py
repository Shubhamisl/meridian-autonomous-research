from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.meridian.infrastructure.database.session import engine, async_sessionmaker
from src.meridian.infrastructure.database.models import DBResearchJob, DBResearchReport
from src.meridian.domain.entities import ResearchJob
from src.meridian.infrastructure.database.sqlite_repositories import SQLiteResearchJobRepository, SQLiteResearchReportRepository
from src.meridian.infrastructure.auth.firebase_auth import get_current_user
from src.meridian.interfaces.api.schemas.research_workspace import (
    EvidenceItem,
    ExplainabilityPayload,
    ResearchWorkspaceResponse,
)
from src.meridian.interfaces.workers.tasks import run_research_pipeline
import logging

try:
    from src.meridian.infrastructure.vector_store.chroma_repository import ChromaChunkRepository
except ImportError:
    ChromaChunkRepository = None

router = APIRouter()
SessionLocal = async_sessionmaker(bind=engine, autoflush=False, autocommit=False)
PHASES = ["research", "chunk", "retrieve", "synthesize"]

async def get_db():
    async with SessionLocal() as session:
        yield session

class ResearchRequest(BaseModel):
    query: str

class ResearchResponse(BaseModel):
    id: str
    status: str
    query: str | None = None


def _workspace_metadata(entity: object | None) -> dict:
    metadata = getattr(entity, "metadata", {}) if entity else {}
    return metadata if isinstance(metadata, dict) else {}


def build_evidence_items(chunks: list) -> list[EvidenceItem]:
    evidence_items: list[EvidenceItem] = []
    seen: set[tuple[str | None, str | None, str | None]] = set()

    for chunk in chunks:
        chunk_metadata = chunk.metadata if isinstance(chunk.metadata, dict) else {}
        source = chunk_metadata.get("source") or "unknown"
        title = chunk_metadata.get("title") or "Untitled source"
        url = chunk_metadata.get("url")
        key = (source, title, url)
        if key in seen:
            continue
        seen.add(key)
        evidence_items.append(
            EvidenceItem(
                source=source,
                title=title,
                url=url,
                credibility_score=float(getattr(chunk, "credibility_score", 0.5) or 0.5),
                snippet=chunk_metadata.get("snippet") or getattr(chunk, "content", None),
            )
        )

    return evidence_items


def build_explainability_payload(metadata: dict) -> ExplainabilityPayload:
    active_sources = metadata.get("active_sources", [])
    if not isinstance(active_sources, list):
        active_sources = []

    query_refinements = metadata.get("query_refinements", [])
    if not isinstance(query_refinements, list):
        query_refinements = []

    normalized_refinements: list[dict[str, str]] = []
    for item in query_refinements:
        if not isinstance(item, dict):
            continue
        source = item.get("source")
        raw_query = item.get("raw_query")
        enriched_query = item.get("enriched_query")
        if not all(isinstance(value, str) and value for value in (source, raw_query, enriched_query)):
            continue
        normalized_refinements.append(
            {
                "source": source,
                "raw_query": raw_query,
                "enriched_query": enriched_query,
            }
        )

    if not normalized_refinements:
        query = metadata.get("query")
        if isinstance(query, str) and query:
            normalized_refinements = [
                {
                    "source": source,
                    "raw_query": query,
                    "enriched_query": query,
                }
                for source in active_sources
                if isinstance(source, str) and source
            ]

    return ExplainabilityPayload(
        active_sources=[source for source in active_sources if isinstance(source, str) and source],
        query_refinements=normalized_refinements,
    )

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
         
    return ResearchResponse(id=job.id, status=job.status, query=job.query)

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
    return [ResearchResponse(id=j.id, status=j.status, query=j.query) for j in jobs]

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
        
    return ResearchResponse(id=job.id, status=job.status, query=job.query)

@router.get("/{job_id}/report", response_model=ResearchWorkspaceResponse)
async def get_research_report(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    job_repo = SQLiteResearchJobRepository(db)
    report_repo = SQLiteResearchReportRepository(db)
    job = await job_repo.get(job_id)
    report = await report_repo.get_by_job_id(job_id)
    
    if not job or not report:
        raise HTTPException(status_code=404, detail="Report not ready yet or job failed.")

    workspace_metadata = {**_workspace_metadata(job), **_workspace_metadata(report)}
    workspace_metadata.setdefault("query", report.query)
    evidence_chunks = []
    if ChromaChunkRepository is not None:
        try:
            chunk_repo = ChromaChunkRepository()
            evidence_chunks = await chunk_repo.search(job_id, query=report.query, top_k=10)
        except Exception as exc:
            logging.warning("Failed to load evidence for job %s: %s", job_id, exc)

    pipeline_metadata = workspace_metadata.get("pipeline")
    current_phase = None
    phases = list(PHASES)
    if isinstance(pipeline_metadata, dict):
        current_phase = pipeline_metadata.get("current_phase")
        stored_phases = pipeline_metadata.get("phases")
        if isinstance(stored_phases, list) and all(isinstance(phase, str) for phase in stored_phases):
            phases = stored_phases

    if not isinstance(current_phase, str) or not current_phase:
        raw_phase = workspace_metadata.get("current_phase")
        current_phase = raw_phase if isinstance(raw_phase, str) and raw_phase else getattr(job.status, "value", str(job.status))

    return ResearchWorkspaceResponse(
        id=report.id,
        job_id=report.job_id,
        query=report.query,
        markdown_content=report.markdown_content,
        domain=workspace_metadata.get("domain"),
        format_label=workspace_metadata.get("format_label"),
        pipeline={"current_phase": current_phase, "phases": phases},
        evidence=build_evidence_items(evidence_chunks),
        explainability=build_explainability_payload(workspace_metadata),
    )
