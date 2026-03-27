import logging
from typing import Any

from src.meridian.application.pipeline.format_selector import FormatSelector
from src.meridian.domain.repositories import ResearchJobRepository, ResearchReportRepository, ChunkRepository
from src.meridian.infrastructure.llm.research_agent import ResearchAgent
from src.meridian.infrastructure.llm.synthesizer import ReportSynthesizer
from src.meridian.application.pipeline.chunking import ChunkingService

logger = logging.getLogger(__name__)
PIPELINE_PHASES = ["research", "chunk", "retrieve", "synthesize"]


def _attach_metadata(model: Any, metadata: dict[str, Any]) -> Any:
    object.__setattr__(model, "metadata", metadata)
    return model


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

        workspace_metadata = dict(getattr(job, "metadata", {}) or {})
        try:
            _update_pipeline_phase(workspace_metadata, "research")
            job = job.start()
            _attach_metadata(job, workspace_metadata)
            await self.job_repo.save(job)

            # Phase 1: Research Agent loop
            documents = await self.agent.run(topic=job.query)
            workspace_metadata["domain"] = getattr(self.agent, "domain", "general")
            workspace_metadata["active_sources"] = _unique_in_order(
                list(getattr(self.agent, "active_sources", []))
                or [document.source for document in documents]
            )
            workspace_metadata["query_refinements"] = _normalize_query_refinements(
                getattr(self.agent, "query_refinements", [])
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
            _attach_metadata(report, dict(workspace_metadata))

            await self.report_repo.save(report)
            
            job = job.complete()
            _attach_metadata(job, workspace_metadata)
            await self.job_repo.save(job)
            return report

        except Exception as e:
            job = job.fail(error_message=str(e))
            _attach_metadata(job, workspace_metadata)
            await self.job_repo.save(job)
