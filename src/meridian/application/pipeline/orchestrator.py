from contextlib import asynccontextmanager
import logging
from typing import Any, Protocol

from src.meridian.application.pipeline.chunking import ChunkingService
from src.meridian.application.pipeline.format_selector import FormatSelector
from src.meridian.domain.repositories import ChunkRepository, ResearchJobRepository, ResearchReportRepository
from src.meridian.infrastructure.llm.research_agent import ResearchAgent
from src.meridian.infrastructure.llm.synthesizer import ReportSynthesizer

logger = logging.getLogger(__name__)
PIPELINE_PHASES = ["research", "chunk", "retrieve", "synthesize"]


class WorkspaceMetadataStore(Protocol):
    async def get_workspace_metadata(self, entity_id: str) -> dict[str, Any]:
        ...

    async def save_workspace_metadata(self, entity_id: str, metadata: dict[str, Any]) -> None:
        ...


class TransactionManager(Protocol):
    async def commit(self) -> None:
        ...

    def begin(self):
        ...


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


def _derive_query_refinements(
    query: str,
    sources: list[str],
    domain: str,
    recorded: Any,
) -> list[dict[str, str]]:
    normalized = _normalize_query_refinements(recorded)
    if normalized:
        return normalized

    from src.meridian.application.pipeline.query_processor import QueryProcessor

    processor = QueryProcessor()
    derived: list[dict[str, str]] = []
    for source in _unique_in_order(sources):
        enriched_query = processor.enrich(query, domain, source)
        derived.append(
            {
                "source": source,
                "raw_query": query,
                "enriched_query": enriched_query,
            }
        )
    return derived


class PipelineOrchestrator:
    def __init__(
        self,
        job_repo: ResearchJobRepository,
        report_repo: ResearchReportRepository,
        job_metadata_store: WorkspaceMetadataStore,
        report_metadata_store: WorkspaceMetadataStore,
        chunk_repo: ChunkRepository,
        agent: ResearchAgent,
        synthesizer: ReportSynthesizer,
        chunking_service: ChunkingService,
        format_selector: FormatSelector,
        transaction_manager: TransactionManager | None = None,
    ):
        self.job_repo = job_repo
        self.report_repo = report_repo
        self.job_metadata_store = job_metadata_store
        self.report_metadata_store = report_metadata_store
        self.chunk_repo = chunk_repo
        self.agent = agent
        self.synthesizer = synthesizer
        self.chunking_service = chunking_service
        self.format_selector = format_selector
        self.transaction_manager = transaction_manager

    async def _commit_pending(self) -> None:
        if self.transaction_manager is not None:
            await self.transaction_manager.commit()

    @asynccontextmanager
    async def _transaction(self):
        if self.transaction_manager is None:
            yield
            return

        async with self.transaction_manager.begin():
            yield

    async def run_pipeline(self, job_id: str):
        job = await self.job_repo.get(job_id)
        if not job:
            return

        workspace_metadata = await self.job_metadata_store.get_workspace_metadata(job.id)
        try:
            _update_pipeline_phase(workspace_metadata, "research")
            job = job.start()
            await self.job_repo.save(job)
            await self.job_metadata_store.save_workspace_metadata(job.id, workspace_metadata)
            await self._commit_pending()

            execution_query = workspace_metadata.get("execution_query")
            if not isinstance(execution_query, str) or not execution_query:
                execution_query = job.query
            documents = await self.agent.run(topic=execution_query)
            workspace_metadata["domain"] = getattr(self.agent, "domain", "general")
            active_sources = _unique_in_order(
                [document.source for document in documents]
                or list(getattr(self.agent, "active_sources", []))
            )
            workspace_metadata["active_sources"] = active_sources
            domain = workspace_metadata["domain"]
            workspace_metadata["query_refinements"] = _derive_query_refinements(
                job.query,
                active_sources,
                domain,
                getattr(self.agent, "query_refinements", []),
            )

            _update_pipeline_phase(workspace_metadata, "chunk")
            await self.job_metadata_store.save_workspace_metadata(job.id, workspace_metadata)
            await self._commit_pending()
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

            _update_pipeline_phase(workspace_metadata, "retrieve")
            await self.job_metadata_store.save_workspace_metadata(job.id, workspace_metadata)
            await self._commit_pending()
            retrieved_chunks = await self.chunk_repo.search(job_id, query=execution_query, top_k=10)

            if not retrieved_chunks:
                retrieved_chunks = all_chunks[:10]

            domain = workspace_metadata.get("domain", getattr(self.agent, "domain", "general"))
            format_label = await self.format_selector.select(domain, execution_query)
            logger.info("Selected report format: %s", format_label)
            workspace_metadata["format_label"] = format_label
            _update_pipeline_phase(workspace_metadata, "synthesize")
            await self.job_metadata_store.save_workspace_metadata(job.id, workspace_metadata)
            await self._commit_pending()

            report = await self.synthesizer.synthesize(
                job_id,
                job.query,
                retrieved_chunks,
                format_label=format_label,
            )
            async with self._transaction():
                await self.report_repo.save(report)
                await self.report_metadata_store.save_workspace_metadata(report.id, workspace_metadata)

                job = job.complete()
                await self.job_repo.save(job)
                await self.job_metadata_store.save_workspace_metadata(job.id, workspace_metadata)
            return report

        except Exception as e:
            async with self._transaction():
                job = job.fail(error_message=str(e))
                await self.job_repo.save(job)
                await self.job_metadata_store.save_workspace_metadata(job.id, workspace_metadata)
