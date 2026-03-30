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
    PipelinePayload,
    QueryRefinement,
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
    execution_query: str | None = None

class ResearchResponse(BaseModel):
    id: str
    status: str
    query: str | None = None


def _display_query(metadata: dict, fallback: str) -> str:
    candidate = metadata.get("display_query")
    return candidate if isinstance(candidate, str) and candidate else fallback


def _ensure_job_owner(job: ResearchJob, user: dict) -> None:
    if job.user_id != user["uid"]:
        raise HTTPException(status_code=404, detail="Job not found")


async def _workspace_metadata(
    repository: SQLiteResearchJobRepository | SQLiteResearchReportRepository,
    entity_id: str | None,
) -> dict:
    if not entity_id:
        return {}
    metadata = await repository.get_workspace_metadata(entity_id)
    return metadata if isinstance(metadata, dict) else {}


def _chunk_credibility_score(chunk: object) -> float:
    raw_score = getattr(chunk, "credibility_score", None)
    if raw_score is None:
        return 0.5
    return float(raw_score)


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
                credibility_score=_chunk_credibility_score(chunk),
                snippet=chunk_metadata.get("snippet") or getattr(chunk, "content", None),
            )
        )

    return evidence_items


def build_explainability_payload(
    metadata: dict,
    *,
    query: str,
    domain: str | None,
    execution_query: str | None = None,
) -> ExplainabilityPayload:
    active_sources = metadata.get("active_sources", [])
    if not isinstance(active_sources, list):
        active_sources = []

    query_refinements = metadata.get("query_refinements", [])
    if not isinstance(query_refinements, list):
        query_refinements = []

    normalized_refinements: list[QueryRefinement] = []
    for item in query_refinements:
        if not isinstance(item, dict):
            continue
        source = item.get("source")
        raw_query = item.get("raw_query")
        enriched_query = item.get("enriched_query")
        if not all(isinstance(value, str) and value for value in (source, raw_query, enriched_query)):
            continue
        normalized_refinements.append(
            QueryRefinement(
                source=source,
                raw_query=raw_query,
                enriched_query=enriched_query,
            )
        )

    if not normalized_refinements and active_sources:
        from src.meridian.application.pipeline.query_processor import QueryProcessor

        processor = QueryProcessor()
        fallback_query = execution_query if isinstance(execution_query, str) and execution_query else query
        normalized_refinements = [
            QueryRefinement(
                source=source,
                raw_query=fallback_query,
                enriched_query=processor.enrich(fallback_query, domain or "general", source),
            )
            for source in active_sources
            if isinstance(source, str) and source
        ]

    return ExplainabilityPayload(
        active_sources=[source for source in active_sources if isinstance(source, str) and source],
        query_refinements=normalized_refinements,
    )


def _normalize_pipeline_phase(candidate: object) -> str | None:
    return candidate if isinstance(candidate, str) and candidate in PHASES else None


@router.post("/", response_model=ResearchResponse)
async def create_research(
    request: ResearchRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    job_repo = SQLiteResearchJobRepository(db)
    job = ResearchJob(query=request.query, user_id=user["uid"])

    await job_repo.save(job)
    workspace_metadata = await job_repo.get_workspace_metadata(job.id)
    workspace_metadata["display_query"] = request.query
    workspace_metadata["execution_query"] = request.execution_query or request.query
    await job_repo.save_workspace_metadata(job.id, workspace_metadata)
    await db.commit()

    try:
        run_research_pipeline.delay(job.id)
    except Exception as e:
        logging.error(f"Failed to queue task: {e}")
        job = job.fail(error_message=str(e))
        await job_repo.save(job)
        await db.commit()

    return ResearchResponse(
        id=job.id,
        status=job.status,
        query=_display_query(workspace_metadata, job.query),
    )

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
    responses = []
    for job in jobs:
        metadata = await SQLiteResearchJobRepository(db).get_workspace_metadata(job.id)
        responses.append(
            ResearchResponse(
                id=job.id,
                status=job.status,
                query=_display_query(metadata, job.query),
            )
        )
    return responses

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
    _ensure_job_owner(job, user)

    metadata = await job_repo.get_workspace_metadata(job.id)
    return ResearchResponse(id=job.id, status=job.status, query=_display_query(metadata, job.query))

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
    _ensure_job_owner(job, user)

    workspace_metadata = {
        **(await _workspace_metadata(job_repo, job.id)),
        **(await _workspace_metadata(report_repo, report.id)),
    }
    response_query = _display_query(workspace_metadata, report.query)
    workspace_metadata.setdefault("query", response_query)
    evidence_chunks = []
    if ChromaChunkRepository is not None:
        try:
            chunk_repo = ChromaChunkRepository()
            evidence_query = workspace_metadata.get("execution_query")
            if not isinstance(evidence_query, str) or not evidence_query:
                evidence_query = report.query
            evidence_chunks = await chunk_repo.search(job_id, query=evidence_query, top_k=10)
        except Exception as exc:
            logging.warning("Failed to load evidence for job %s: %s", job_id, exc)

    pipeline_metadata = workspace_metadata.get("pipeline")
    current_phase = None
    phases = list(PHASES)
    if isinstance(pipeline_metadata, dict):
        current_phase = _normalize_pipeline_phase(pipeline_metadata.get("current_phase"))
        stored_phases = pipeline_metadata.get("phases")
        if isinstance(stored_phases, list) and all(isinstance(phase, str) for phase in stored_phases):
            phases = stored_phases

    if current_phase is None:
        current_phase = _normalize_pipeline_phase(workspace_metadata.get("current_phase"))

    return ResearchWorkspaceResponse(
        id=report.id,
        job_id=report.job_id,
        query=response_query,
        markdown_content=report.markdown_content,
        domain=workspace_metadata.get("domain"),
        format_label=workspace_metadata.get("format_label"),
        pipeline=PipelinePayload(current_phase=current_phase, phases=phases),
        evidence=build_evidence_items(evidence_chunks),
        explainability=build_explainability_payload(
            workspace_metadata,
            query=response_query,
            domain=workspace_metadata.get("domain"),
            execution_query=workspace_metadata.get("execution_query"),
        ),
    )
