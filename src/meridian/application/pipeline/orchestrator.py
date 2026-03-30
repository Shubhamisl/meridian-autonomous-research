from contextlib import asynccontextmanager
import logging
from typing import Any, Protocol

from src.meridian.application.pipeline.coverage_gate import CoverageGate, InsufficientRelevantEvidenceError
from src.meridian.application.pipeline.chunking import ChunkingService
from src.meridian.application.pipeline.evidence_selection import EvidenceSelectionService
from src.meridian.application.pipeline.format_selector import FormatSelector
from src.meridian.application.pipeline.reliability_policy import ReliabilityPolicy
from src.meridian.domain.repositories import ChunkRepository, ResearchJobRepository, ResearchReportRepository
from src.meridian.infrastructure.llm.research_agent import ResearchAgent
from src.meridian.infrastructure.llm.synthesizer import ReportSynthesizer

logger = logging.getLogger(__name__)
PIPELINE_PHASES = ["research", "select", "chunk", "retrieve", "synthesize"]


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
        source_query = item.get("source_query")
        if not all(isinstance(value, str) and value for value in (source, raw_query, enriched_query)):
            continue
        payload = {
            "source": source,
            "raw_query": raw_query,
            "enriched_query": enriched_query,
        }
        if isinstance(source_query, str) and source_query:
            payload["source_query"] = source_query
        normalized.append(payload)
    return normalized


def _normalize_advanced_options(options: Any) -> dict[str, Any]:
    normalized = {
        "recentOnly": True,
        "requireMultipleSources": True,
        "reportDepth": "standard",
    }
    if not isinstance(options, dict):
        return normalized

    if isinstance(options.get("recentOnly"), bool):
        normalized["recentOnly"] = options["recentOnly"]
    if isinstance(options.get("requireMultipleSources"), bool):
        normalized["requireMultipleSources"] = options["requireMultipleSources"]
    if options.get("reportDepth") in {"standard", "deep"}:
        normalized["reportDepth"] = options["reportDepth"]
    return normalized


def _selection_decision_payload(decision: Any) -> dict[str, Any]:
    return {
        "document_id": getattr(decision.document, "id", None),
        "source": getattr(decision.document, "source", None),
        "title": getattr(decision.document, "title", None),
        "url": getattr(decision.document, "url", None),
        "reason": decision.reason,
        "relevance_score": decision.relevance_score,
        "scorer_reason": getattr(decision, "scorer_reason", None),
        "scorer_detail": getattr(decision, "scorer_detail", None),
        "adjudication_detail": getattr(decision, "adjudication_detail", None),
        "source_query": getattr(decision, "source_query", None),
        "llm_attempted": getattr(decision, "llm_attempted", False),
        "llm_success": getattr(decision, "llm_success", False),
        "credibility_score": getattr(decision, "credibility_score", None),
    }


def _selection_metadata(selection_result: Any) -> dict[str, Any]:
    return {
        "query": getattr(selection_result, "query", None),
        "domain": getattr(selection_result, "domain", None),
        "source_queries": {
            source: list(queries)
            for source, queries in (getattr(selection_result, "source_queries", {}) or {}).items()
        },
        "accepted_count": len(getattr(selection_result, "accepted", []) or []),
        "rejected_count": len(getattr(selection_result, "rejected", []) or []),
        "llm_budget_limit": getattr(selection_result, "llm_budget_limit", None),
        "llm_budget_used": getattr(selection_result, "llm_budget_used", None),
        "llm_budget_remaining": getattr(selection_result, "llm_budget_remaining", None),
        "accepted": [_selection_decision_payload(decision) for decision in getattr(selection_result, "accepted", []) or []],
        "rejected": [_selection_decision_payload(decision) for decision in getattr(selection_result, "rejected", []) or []],
    }


def _coverage_metadata(verdict: Any) -> dict[str, Any]:
    return {
        "domain": getattr(verdict, "domain", None),
        "action": getattr(verdict, "action", None),
        "reason": getattr(verdict, "reason", None),
        "accepted_count": getattr(verdict, "accepted_count", None),
        "distinct_sources": getattr(verdict, "distinct_sources", None),
        "average_relevance": getattr(verdict, "average_relevance", None),
        "source_distribution": dict(getattr(verdict, "source_distribution", {}) or {}),
        "query_family_distribution": dict(getattr(verdict, "query_family_distribution", {}) or {}),
        "required_documents": getattr(verdict, "required_documents", None),
        "required_sources": getattr(verdict, "required_sources", None),
        "required_average_relevance": getattr(verdict, "required_average_relevance", None),
        "message": verdict.failure_message() if hasattr(verdict, "failure_message") and getattr(verdict, "action", "") != "synthesize" else "coverage_sufficient",
    }


def _source_queries_from_refinements(query_refinements: Any) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for item in _normalize_query_refinements(query_refinements):
        compiled = item.get("source_query")
        query_value = compiled if isinstance(compiled, str) and compiled else item["enriched_query"]
        mapping.setdefault(item["source"], []).append(query_value)
    return mapping


def _source_distribution(decisions: list[Any]) -> dict[str, int]:
    distribution: dict[str, int] = {}
    for decision in decisions:
        source = getattr(getattr(decision, "document", None), "source", None)
        if not isinstance(source, str) or not source:
            continue
        distribution[source] = distribution.get(source, 0) + 1
    return distribution


def _query_family_distribution(decisions: list[Any]) -> dict[str, int]:
    distribution: dict[str, int] = {}
    for decision in decisions:
        document = getattr(decision, "document", None)
        source = getattr(document, "source", None)
        source_query = getattr(decision, "source_query", None) or "unknown_query"
        if not isinstance(source, str) or not source:
            continue
        key = f"{source}::{source_query}"
        distribution[key] = distribution.get(key, 0) + 1
    return distribution


def _attach_selection_credibility_scores(metadata: dict[str, Any], chunks: list[Any]) -> None:
    selection = metadata.get("selection")
    if not isinstance(selection, dict):
        return

    credibility_by_document_id: dict[str, float] = {}
    for chunk in chunks:
        document_id = getattr(chunk, "document_id", None)
        if not isinstance(document_id, str) or not document_id:
            continue
        if document_id not in credibility_by_document_id:
            credibility_by_document_id[document_id] = float(getattr(chunk, "credibility_score", 0.5))

    accepted = selection.get("accepted")
    if not isinstance(accepted, list):
        return

    for item in accepted:
        if not isinstance(item, dict):
            continue
        document_id = item.get("document_id")
        if isinstance(document_id, str) and document_id in credibility_by_document_id:
            item["credibility_score"] = credibility_by_document_id[document_id]


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
        evidence_selection_service: EvidenceSelectionService | None = None,
        coverage_gate: CoverageGate | None = None,
        reliability_policy: ReliabilityPolicy | None = None,
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
        self.reliability_policy = reliability_policy or getattr(evidence_selection_service, "policy", None) or getattr(coverage_gate, "policy", None) or ReliabilityPolicy()
        self.evidence_selection_service = evidence_selection_service or EvidenceSelectionService(policy=self.reliability_policy)
        self.coverage_gate = coverage_gate or CoverageGate(self.reliability_policy)
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
            advanced_options = _normalize_advanced_options(workspace_metadata.get("advanced_options"))
            workspace_metadata["advanced_options"] = advanced_options
            _update_pipeline_phase(workspace_metadata, "research")
            job = job.start()
            await self.job_repo.save(job)
            await self.job_metadata_store.save_workspace_metadata(job.id, workspace_metadata)
            await self._commit_pending()

            execution_query = workspace_metadata.get("execution_query")
            if not isinstance(execution_query, str) or not execution_query:
                execution_query = job.query
            documents = await self.agent.run(
                topic=execution_query,
                require_multiple_sources=advanced_options["requireMultipleSources"],
            )
            workspace_metadata["domain"] = getattr(self.agent, "domain", "general")
            active_sources = _unique_in_order(
                [document.source for document in documents]
                or list(getattr(self.agent, "active_sources", []))
            )
            workspace_metadata["active_sources"] = active_sources
            domain = workspace_metadata["domain"]
            workspace_metadata["query_refinements"] = _derive_query_refinements(
                execution_query,
                active_sources,
                domain,
                getattr(self.agent, "query_refinements", []),
            )

            selection_source_queries = _source_queries_from_refinements(workspace_metadata["query_refinements"])
            _update_pipeline_phase(workspace_metadata, "select")
            selection_result = await self.evidence_selection_service.select(
                query=job.query,
                domain=domain,
                candidates=documents,
                source_queries=selection_source_queries,
            )
            selected_documents = [decision.document for decision in selection_result.accepted]
            accepted_count = len(selection_result.accepted)
            distinct_sources = len(_unique_in_order([document.source for document in selected_documents]))
            average_relevance = (
                sum(decision.relevance_score for decision in selection_result.accepted) / accepted_count
                if accepted_count
                else 0.0
            )
            source_distribution = _source_distribution(selection_result.accepted)
            query_family_distribution = _query_family_distribution(selection_result.accepted)
            coverage_verdict = self.coverage_gate.evaluate(
                domain=domain,
                accepted_count=accepted_count,
                distinct_sources=distinct_sources,
                average_relevance=average_relevance,
                source_distribution=source_distribution,
                query_family_distribution=query_family_distribution,
            )
            workspace_metadata["selection"] = _selection_metadata(selection_result)
            workspace_metadata["coverage"] = _coverage_metadata(coverage_verdict)
            await self.job_metadata_store.save_workspace_metadata(job.id, workspace_metadata)
            await self._commit_pending()

            if getattr(coverage_verdict, "action", "retry") != "synthesize":
                raise InsufficientRelevantEvidenceError(coverage_verdict)

            _update_pipeline_phase(workspace_metadata, "chunk")
            await self.job_metadata_store.save_workspace_metadata(job.id, workspace_metadata)
            await self._commit_pending()
            all_chunks = await self.chunking_service.chunk_documents(selected_documents)
            for document in selected_documents:
                document_chunks = [chunk for chunk in all_chunks if chunk.document_id == document.id]
                credibility_score = document_chunks[0].credibility_score if document_chunks else 0.5

                logger.info(
                    "Chunked document summary: source=%s title=%s credibility_score=%.2f",
                    document.source,
                    document.title[:60],
                    credibility_score,
                )

            await self.chunk_repo.save_all(job_id, all_chunks)
            _attach_selection_credibility_scores(workspace_metadata, all_chunks)

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
                report_depth=advanced_options["reportDepth"],
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
