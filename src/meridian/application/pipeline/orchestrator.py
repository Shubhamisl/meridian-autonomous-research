import logging
from typing import Any

from src.meridian.application.pipeline.format_selector import FormatSelector
from src.meridian.domain.repositories import ResearchJobRepository, ResearchReportRepository, ChunkRepository
from src.meridian.infrastructure.llm.research_agent import ResearchAgent
from src.meridian.infrastructure.llm.synthesizer import ReportSynthesizer
from src.meridian.application.pipeline.chunking import ChunkingService

logger = logging.getLogger(__name__)
PIPELINE_PHASES = ["research", "chunk", "retrieve", "synthesize"]


def _update_pipeline_phase(metadata: dict[str, Any], phase: str) -> None:
    metadata["current_phase"] = phase
    metadata["pipeline"] = {"current_phase": phase, "phases": list(PIPELINE_PHASES)}


def _unique_in_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _normalize_query_refinements(query_refinements: Any) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    if not isinstance(query_refinements, list):
        return normalized

    for item in query_refinements:
        if not isinstance(item, dict):
            continue
        source = item.get("source")
        raw_query = item.get("raw_query")
        enriched_query = item.get("enriched_query")
        if not all(isinstance(value, str) and value for value in (source, raw_query, enriched_query)):
            continue
        normalized.append(
            {
                "source": source,
                "raw_query": raw_query,
                "enriched_query": enriched_query,
            }
        )
    return normalized


def _derive_query_refinements(query: str, sources: list[str], recorded: Any) -> list[dict[str, str]]:
    normalized = _normalize_query_refinements(recorded)
    if normalized:
        return normalized
    return []


async def _load_workspace_metadata(repository: object, entity_id: str) -> dict[str, Any]:
    loader = getattr(repository, "get_workspace_metadata", None)
    if not callable(loader):
        return {}

    metadata = await loader(entity_id)
    return metadata if isinstance(metadata, dict) else {}


async def _save_workspace_metadata(repository: object, entity_id: str, metadata: dict[str, Any]) -> None:
    saver = getattr(repository, "save_workspace_metadata", None)
    if callable(saver):
        await saver(entity_id, dict(metadata))

class PipelineOrchestrator:
    def __init__(
        self,
        job_repo: ResearchJobRepository,
        report_repo: ResearchReportRepository,
        chunk_repo: ChunkRepository,
        agent: ResearchAgent,
        synthesizer: ReportSynthesizer,
        chunking_service: ChunkingService,
        format_selector: FormatSelector,
    ):
        self.job_repo = job_repo
        self.report_repo = report_repo
        self.chunk_repo = chunk_repo
        self.agent = agent
        self.synthesizer = synthesizer
        self.chunking_service = chunking_service
        self.format_selector = format_selector

    async def run_pipeline(self, job_id: str):
        job = await self.job_repo.get(job_id)
        if not job:
            return

        workspace_metadata = await _load_workspace_metadata(self.job_repo, job.id)
        try:
            _update_pipeline_phase(workspace_metadata, "research")
            job = job.start()
            await self.job_repo.save(job)
            await _save_workspace_metadata(self.job_repo, job.id, workspace_metadata)

            # Phase 1: Research Agent loop
            documents = await self.agent.run(topic=job.query)
            workspace_metadata["domain"] = getattr(self.agent, "domain", "general")
            active_sources = _unique_in_order(
                [document.source for document in documents]
                or list(getattr(self.agent, "active_sources", []))
            )
            workspace_metadata["active_sources"] = active_sources
            workspace_metadata["query_refinements"] = _derive_query_refinements(
                job.query,
                active_sources,
                getattr(self.agent, "query_refinements", []),
            )

            # Phase 2: Chunk & Embed
            _update_pipeline_phase(workspace_metadata, "chunk")
            all_chunks = await self.chunking_service.chunk_documents(documents)
            for document in documents:
                document_chunks = [chunk for chunk in all_chunks if chunk.document_id == document.id]
                credibility_score = document_chunks[0].credibility_score if document_chunks else 0.5

                logger.info(
                    "Chunked document summary: source=%s title=%s credibility_score=%.2f",
                    document.source,
                    document.title[:60],
                    credibility_score,
                )

            await self.chunk_repo.save_all(job_id, all_chunks)

            # Phase 3 & 4: RAG Retrieval and Synthesis
            _update_pipeline_phase(workspace_metadata, "retrieve")
            retrieved_chunks = await self.chunk_repo.search(job_id, query=job.query, top_k=10)
            
            if not retrieved_chunks:
                retrieved_chunks = all_chunks[:10]

            domain = workspace_metadata.get("domain", getattr(self.agent, "domain", "general"))
            format_label = await self.format_selector.select(domain, job.query)
            logger.info("Selected report format: %s", format_label)
            workspace_metadata["format_label"] = format_label
            _update_pipeline_phase(workspace_metadata, "synthesize")

            report = await self.synthesizer.synthesize(
                job_id,
                job.query,
                retrieved_chunks,
                format_label=format_label,
            )
            await self.report_repo.save(report)
            await _save_workspace_metadata(self.report_repo, report.id, workspace_metadata)
            
            job = job.complete()
            await self.job_repo.save(job)
            await _save_workspace_metadata(self.job_repo, job.id, workspace_metadata)
            return report

        except Exception as e:
            job = job.fail(error_message=str(e))
            await self.job_repo.save(job)
            await _save_workspace_metadata(self.job_repo, job.id, workspace_metadata)
