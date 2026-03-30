from typing import Literal

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
    CoveragePayload,
    EvidenceItem,
    ExplainabilityPayload,
    PipelinePayload,
    QueryRefinement,
    ResearchWorkspaceResponse,
    SelectionDecisionPayload,
    SelectionPayload,
)
from src.meridian.interfaces.workers.tasks import run_research_pipeline
import logging

try:
    from src.meridian.infrastructure.vector_store.chroma_repository import ChromaChunkRepository
except ImportError:
    ChromaChunkRepository = None

router = APIRouter()
SessionLocal = async_sessionmaker(bind=engine, autoflush=False, autocommit=False)
PHASES = ["research", "select", "chunk", "retrieve", "synthesize"]

async def get_db():
    async with SessionLocal() as session:
        yield session

class ResearchRequest(BaseModel):
    query: str
    execution_query: str | None = None
    advanced_options: "AdvancedResearchOptionsRequest | None" = None


class AdvancedResearchOptionsRequest(BaseModel):
    recentOnly: bool = True
    requireMultipleSources: bool = True
    reportDepth: Literal["standard", "deep"] = "standard"

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

    selection = _build_selection_payload(metadata.get("selection"))
    coverage = _build_coverage_payload(metadata.get("coverage"))

    return ExplainabilityPayload(
        active_sources=[source for source in active_sources if isinstance(source, str) and source],
        query_refinements=normalized_refinements,
        selection=selection,
        coverage=coverage,
    )


def _build_selection_payload(selection: object) -> SelectionPayload | None:
    if not isinstance(selection, dict):
        return None

    return SelectionPayload(
        accepted_count=_as_int(selection.get("accepted_count"), 0),
        rejected_count=_as_int(selection.get("rejected_count"), 0),
        source_queries=_normalize_source_query_map(selection.get("source_queries")),
        llm_budget_limit=_optional_int(selection.get("llm_budget_limit")),
        llm_budget_used=_optional_int(selection.get("llm_budget_used")),
        llm_budget_remaining=_optional_int(selection.get("llm_budget_remaining")),
        accepted=_build_selection_decisions(selection.get("accepted")),
        rejected=_build_selection_decisions(selection.get("rejected")),
    )


def _build_coverage_payload(coverage: object) -> CoveragePayload | None:
    if not isinstance(coverage, dict):
        return None

    return CoveragePayload(
        action=_optional_str(coverage.get("action")),
        reason=_optional_str(coverage.get("reason")),
        accepted_count=_optional_int(coverage.get("accepted_count")),
        distinct_sources=_optional_int(coverage.get("distinct_sources")),
        average_relevance=_optional_float(coverage.get("average_relevance")),
        source_distribution=_normalize_int_map(coverage.get("source_distribution")),
        query_family_distribution=_normalize_int_map(coverage.get("query_family_distribution")),
        required_documents=_optional_int(coverage.get("required_documents")),
        required_sources=_optional_int(coverage.get("required_sources")),
        required_average_relevance=_optional_float(coverage.get("required_average_relevance")),
        message=_optional_str(coverage.get("message")),
    )


def _build_selection_decisions(decisions: object) -> list[SelectionDecisionPayload]:
    if not isinstance(decisions, list):
        return []

    normalized: list[SelectionDecisionPayload] = []
    for item in decisions:
        if not isinstance(item, dict):
            continue
        reason = item.get("reason")
        relevance_score = item.get("relevance_score")
        if not isinstance(reason, str) or not isinstance(relevance_score, (int, float)):
            continue
        normalized.append(
            SelectionDecisionPayload(
                document_id=_optional_str(item.get("document_id")),
                source=_optional_str(item.get("source")),
                title=_optional_str(item.get("title")),
                url=_optional_str(item.get("url")),
                reason=reason,
                relevance_score=float(relevance_score),
                scorer_reason=_optional_str(item.get("scorer_reason")),
                scorer_detail=_optional_str(item.get("scorer_detail")),
                adjudication_detail=_optional_str(item.get("adjudication_detail")),
                source_query=_optional_str(item.get("source_query")),
                credibility_score=_optional_float(item.get("credibility_score")),
                llm_attempted=bool(item.get("llm_attempted", False)),
                llm_success=bool(item.get("llm_success", False)),
            )
        )
    return normalized


def _normalize_source_query_map(raw_mapping: object) -> dict[str, list[str]]:
    if not isinstance(raw_mapping, dict):
        return {}
    normalized: dict[str, list[str]] = {}
    for source, queries in raw_mapping.items():
        if not isinstance(source, str) or not source:
            continue
        if isinstance(queries, list):
            valid_queries = [query for query in queries if isinstance(query, str) and query]
        elif isinstance(queries, str):
            valid_queries = [queries]
        else:
            continue
        if valid_queries:
            normalized[source] = valid_queries
    return normalized


def _normalize_int_map(raw_mapping: object) -> dict[str, int]:
    if not isinstance(raw_mapping, dict):
        return {}
    normalized: dict[str, int] = {}
    for key, value in raw_mapping.items():
        if isinstance(key, str) and isinstance(value, int):
            normalized[key] = value
    return normalized


def _as_int(value: object, default: int) -> int:
    return value if isinstance(value, int) else default


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) else None


def _optional_float(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _optional_str(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


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
    workspace_metadata["advanced_options"] = (
        request.advanced_options.model_dump()
        if request.advanced_options is not None
        else AdvancedResearchOptionsRequest().model_dump()
    )
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
