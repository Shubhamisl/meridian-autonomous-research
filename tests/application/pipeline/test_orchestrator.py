import importlib
import sys
import types

import pytest

from src.meridian.application.pipeline.coverage_gate import CoverageVerdict
from src.meridian.application.pipeline.evidence_selection import EvidenceDecision, EvidenceSelectionResult
from src.meridian.domain.entities import Chunk, Document, ResearchJob, ResearchReport


class FakeJobRepo:
    def __init__(self, job):
        self.job = job
        self.saved_jobs = []

    async def get(self, job_id):
        return self.job

    async def save(self, job):
        self.job = job
        self.saved_jobs.append(job)


class FakeReportRepo:
    def __init__(self):
        self.saved_reports = []

    async def save(self, report):
        self.saved_reports.append(report)


class FakeWorkspaceMetadataStore:
    def __init__(self):
        self.metadata_by_id = {}
        self.saved_metadata = []

    async def get_workspace_metadata(self, entity_id):
        return dict(self.metadata_by_id.get(entity_id, {}))

    async def save_workspace_metadata(self, entity_id, metadata):
        self.metadata_by_id[entity_id] = dict(metadata)
        self.saved_metadata.append((entity_id, dict(metadata)))


class FakeChunkRepo:
    def __init__(self, log=None):
        self.saved_chunks = []
        self.log = log

    async def save_all(self, job_id, chunks):
        self.saved_chunks = list(chunks)

    async def search(self, job_id, query, top_k=5):
        if self.log is not None:
            self.log.append(("chunk_search", job_id, query, top_k))
        return []


class FakeAgent:
    def __init__(self, documents, log=None):
        self.documents = documents
        self.calls = []
        self.domain = "computer_science"
        self.log = log

    async def run(self, topic, max_iterations=5, require_multiple_sources=True):
        self.calls.append(
            {
                "topic": topic,
                "max_iterations": max_iterations,
                "require_multiple_sources": require_multiple_sources,
            }
        )
        if self.log is not None:
            self.log.append(("agent_run", topic, require_multiple_sources))
        return self.documents


class FakeSynthesizer:
    def __init__(self, log=None):
        self.calls = []
        self.log = log

    async def synthesize(self, job_id, query, chunks, format_label, report_depth="standard"):
        self.calls.append(
            {
                "job_id": job_id,
                "query": query,
                "chunks": chunks,
                "format_label": format_label,
                "report_depth": report_depth,
            }
        )
        if self.log is not None:
            self.log.append(("synthesize", job_id, query, len(chunks), report_depth))
        return ResearchReport(job_id=job_id, query=query, markdown_content="report")


class FakeChunkingService:
    def __init__(self, chunks):
        self.chunks = chunks
        self.calls = []

    async def chunk_documents(self, documents):
        self.calls.append(list(documents))
        return self.chunks


class FakeFormatSelector:
    def __init__(self, label="osint"):
        self.label = label
        self.calls = []

    async def select(self, domain, query):
        self.calls.append((domain, query))
        return self.label


class FakeSelectionService:
    def __init__(self, result=None):
        self.result = result
        self.calls = []

    async def select(self, query, domain, candidates, source_queries):
        self.calls.append(
            {
                "query": query,
                "domain": domain,
                "candidates": list(candidates),
                "source_queries": {
                    source: list(queries)
                    for source, queries in source_queries.items()
                },
            }
        )
        if self.result is not None:
            return self.result

        accepted = [
            EvidenceDecision(
                document=document,
                reason="accepted",
                relevance_score=0.9,
                scorer_reason="lexically_relevant",
                scorer_detail="default_accept",
                adjudication_detail="default_accept",
                source_query=source_queries.get(document.source),
            )
            for document in candidates
        ]
        return EvidenceSelectionResult(
            query=query,
            domain=domain,
            source_queries={
                source: list(queries)
                for source, queries in source_queries.items()
            },
            accepted=accepted,
            rejected=[],
            llm_budget_limit=5,
            llm_budget_used=0,
            llm_budget_remaining=5,
        )


class FakeCoverageGate:
    def __init__(self, verdict=None):
        self.verdict = verdict or CoverageVerdict(
            domain="general",
            action="synthesize",
            reason="sufficient_coverage",
            accepted_count=1,
            distinct_sources=1,
            average_relevance=0.9,
            source_distribution={"web": 1},
            query_family_distribution={"web::query": 1},
            required_documents=1,
            required_sources=1,
            required_average_relevance=0.0,
        )
        self.calls = []

    def evaluate(
        self,
        domain,
        accepted_count,
        distinct_sources,
        average_relevance,
        source_distribution=None,
        query_family_distribution=None,
    ):
        self.calls.append(
            {
                "domain": domain,
                "accepted_count": accepted_count,
                "distinct_sources": distinct_sources,
                "average_relevance": average_relevance,
                "source_distribution": dict(source_distribution or {}),
                "query_family_distribution": dict(query_family_distribution or {}),
            }
        )
        return self.verdict


class FakeTransaction:
    def __init__(self, events):
        self.events = events

    async def __aenter__(self):
        self.events.append("begin")
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.events.append(("end", exc_type.__name__ if exc_type else None))
        return False


class FakeTransactionManager:
    def __init__(self):
        self.events = []

    async def commit(self):
        self.events.append("commit")

    def begin(self):
        return FakeTransaction(self.events)


class FailingReportRepo(FakeReportRepo):
    async def save(self, report):
        await super().save(report)
        raise RuntimeError("report save failed")


def _orchestrator_factory(orchestrator_cls, selection_service=None, coverage_gate=None):
    selection_service = selection_service or FakeSelectionService()
    coverage_gate = coverage_gate or FakeCoverageGate()

    def _build_orchestrator(**kwargs):
        evidence_selection_service = kwargs.pop(
            "evidence_selection_service",
            kwargs.pop("selection_service", selection_service),
        )
        active_coverage_gate = kwargs.pop("coverage_gate", coverage_gate)
        return orchestrator_cls(
            **kwargs,
            evidence_selection_service=evidence_selection_service,
            coverage_gate=active_coverage_gate,
        )

    return _build_orchestrator


@pytest.mark.asyncio
async def test_run_pipeline_uses_chunking_service_logs_document_summary_and_passes_format_label(monkeypatch, caplog):
    fake_research_agent_module = types.ModuleType("src.meridian.infrastructure.llm.research_agent")
    fake_research_agent_module.ResearchAgent = object
    fake_synthesizer_module = types.ModuleType("src.meridian.infrastructure.llm.synthesizer")
    fake_synthesizer_module.ReportSynthesizer = object
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.llm.research_agent", fake_research_agent_module)
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.llm.synthesizer", fake_synthesizer_module)

    orchestrator_module = importlib.import_module("src.meridian.application.pipeline.orchestrator")
    PipelineOrchestrator = _orchestrator_factory(orchestrator_module.PipelineOrchestrator)

    job = ResearchJob(query="q")
    document = Document(source="web", url="https://example.com", title="T" * 80, content="content")
    chunk = Chunk(document_id=document.id, content="service chunk", credibility_score=0.87)
    job_repo = FakeJobRepo(job)
    report_repo = FakeReportRepo()
    chunk_repo = FakeChunkRepo()
    agent = FakeAgent([document])
    agent.query_refinements = [
        {
            "source": "arxiv",
            "raw_query": "threat actor report after:2022-01-01",
            "enriched_query": '"threat actor report after:2022-01-01" after:2022-01-01',
        }
    ]
    chunking_service = FakeChunkingService([chunk])
    synthesizer = FakeSynthesizer()
    format_selector = FakeFormatSelector("osint")
    job_metadata_store = FakeWorkspaceMetadataStore()
    report_metadata_store = FakeWorkspaceMetadataStore()

    monkeypatch.setattr(
        "src.meridian.application.pipeline.orchestrator.chunk_document",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("chunk_document should not be called")),
        raising=False,
    )

    orchestrator = PipelineOrchestrator(
        job_repo=job_repo,
        report_repo=report_repo,
        chunk_repo=chunk_repo,
        agent=agent,
        synthesizer=synthesizer,
        chunking_service=chunking_service,
        format_selector=format_selector,
        job_metadata_store=job_metadata_store,
        report_metadata_store=report_metadata_store,
    )

    with caplog.at_level("INFO"):
        await orchestrator.run_pipeline(job.id)

    assert len(chunking_service.calls) == 1
    assert chunking_service.calls[0] == [document]
    assert chunk_repo.saved_chunks == [chunk]
    assert len(report_repo.saved_reports) == 1
    assert format_selector.calls == [("computer_science", job.query)]
    assert synthesizer.calls[0]["format_label"] == "osint"
    assert synthesizer.calls[0]["report_depth"] == "standard"
    assert [
        record.message
        for record in caplog.records
        if record.levelname == "INFO"
    ] == [
        f"Chunked document summary: source=web title={'T' * 60} credibility_score=0.87",
        "Selected report format: osint",
    ]


@pytest.mark.asyncio
async def test_run_pipeline_logs_a_summary_for_empty_document(monkeypatch, caplog):
    fake_research_agent_module = types.ModuleType("src.meridian.infrastructure.llm.research_agent")
    fake_research_agent_module.ResearchAgent = object
    fake_synthesizer_module = types.ModuleType("src.meridian.infrastructure.llm.synthesizer")
    fake_synthesizer_module.ReportSynthesizer = object
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.llm.research_agent", fake_research_agent_module)
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.llm.synthesizer", fake_synthesizer_module)

    orchestrator_module = importlib.import_module("src.meridian.application.pipeline.orchestrator")
    PipelineOrchestrator = _orchestrator_factory(orchestrator_module.PipelineOrchestrator)

    job = ResearchJob(query="q")
    document = Document(source="web", url="https://example.com", title="Empty", content="")
    job_repo = FakeJobRepo(job)
    report_repo = FakeReportRepo()
    chunk_repo = FakeChunkRepo()
    agent = FakeAgent([document])
    chunking_service = FakeChunkingService([])
    synthesizer = FakeSynthesizer()
    format_selector = FakeFormatSelector("general")
    job_metadata_store = FakeWorkspaceMetadataStore()
    report_metadata_store = FakeWorkspaceMetadataStore()

    orchestrator = PipelineOrchestrator(
        job_repo=job_repo,
        report_repo=report_repo,
        chunk_repo=chunk_repo,
        agent=agent,
        synthesizer=synthesizer,
        chunking_service=chunking_service,
        format_selector=format_selector,
        job_metadata_store=job_metadata_store,
        report_metadata_store=report_metadata_store,
    )

    with caplog.at_level("INFO"):
        await orchestrator.run_pipeline(job.id)

    assert [
        record.message
        for record in caplog.records
        if record.levelname == "INFO"
    ] == [
        "Chunked document summary: source=web title=Empty credibility_score=0.50",
        "Selected report format: general",
    ]


@pytest.mark.asyncio
async def test_run_pipeline_uses_general_when_agent_has_no_domain(monkeypatch):
    fake_research_agent_module = types.ModuleType("src.meridian.infrastructure.llm.research_agent")
    fake_research_agent_module.ResearchAgent = object
    fake_synthesizer_module = types.ModuleType("src.meridian.infrastructure.llm.synthesizer")
    fake_synthesizer_module.ReportSynthesizer = object
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.llm.research_agent", fake_research_agent_module)
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.llm.synthesizer", fake_synthesizer_module)

    orchestrator_module = importlib.import_module("src.meridian.application.pipeline.orchestrator")
    PipelineOrchestrator = _orchestrator_factory(orchestrator_module.PipelineOrchestrator)

    job = ResearchJob(query="General topic")
    document = Document(source="web", url="https://example.com", title="T", content="content")
    chunk = Chunk(document_id=document.id, content="service chunk", credibility_score=0.87)
    job_repo = FakeJobRepo(job)
    report_repo = FakeReportRepo()
    chunk_repo = FakeChunkRepo()
    agent = FakeAgent([document])
    delattr(agent, "domain")
    chunking_service = FakeChunkingService([chunk])
    synthesizer = FakeSynthesizer()
    format_selector = FakeFormatSelector("general")
    job_metadata_store = FakeWorkspaceMetadataStore()
    report_metadata_store = FakeWorkspaceMetadataStore()

    orchestrator = PipelineOrchestrator(
        job_repo=job_repo,
        report_repo=report_repo,
        chunk_repo=chunk_repo,
        agent=agent,
        synthesizer=synthesizer,
        chunking_service=chunking_service,
        format_selector=format_selector,
        job_metadata_store=job_metadata_store,
        report_metadata_store=report_metadata_store,
    )

    await orchestrator.run_pipeline(job.id)

    assert format_selector.calls == [("general", job.query)]


@pytest.mark.asyncio
async def test_run_pipeline_persists_workspace_metadata_via_explicit_stores(monkeypatch, caplog):
    fake_research_agent_module = types.ModuleType("src.meridian.infrastructure.llm.research_agent")
    fake_research_agent_module.ResearchAgent = object
    fake_synthesizer_module = types.ModuleType("src.meridian.infrastructure.llm.synthesizer")
    fake_synthesizer_module.ReportSynthesizer = object
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.llm.research_agent", fake_research_agent_module)
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.llm.synthesizer", fake_synthesizer_module)

    orchestrator_module = importlib.import_module("src.meridian.application.pipeline.orchestrator")
    PipelineOrchestrator = _orchestrator_factory(orchestrator_module.PipelineOrchestrator)

    job = ResearchJob(query="threat actor report")
    document = Document(source="arxiv", url="https://example.com/paper", title="Threat Actor Report", content="content")
    chunk = Chunk(
        document_id=document.id,
        content="service chunk",
        metadata={
            "source": "arxiv",
            "title": "Threat Actor Report",
            "url": "https://example.com/paper",
        },
        credibility_score=0.87,
    )
    log = []
    job_repo = FakeJobRepo(job)
    report_repo = FakeReportRepo()
    chunk_repo = FakeChunkRepo(log=log)
    agent = FakeAgent([document], log=log)
    agent.query_refinements = [
        {
            "source": "arxiv",
            "raw_query": "threat actor report after:2022-01-01",
            "enriched_query": '"threat actor report after:2022-01-01" after:2022-01-01',
        }
    ]
    chunking_service = FakeChunkingService([chunk])
    synthesizer = FakeSynthesizer(log=log)
    format_selector = FakeFormatSelector("osint")
    job_metadata_store = FakeWorkspaceMetadataStore()
    report_metadata_store = FakeWorkspaceMetadataStore()
    job_metadata_store.metadata_by_id[job.id] = {
        "execution_query": "threat actor report after:2022-01-01",
    }

    orchestrator = PipelineOrchestrator(
        job_repo=job_repo,
        report_repo=report_repo,
        chunk_repo=chunk_repo,
        agent=agent,
        synthesizer=synthesizer,
        chunking_service=chunking_service,
        format_selector=format_selector,
        job_metadata_store=job_metadata_store,
        report_metadata_store=report_metadata_store,
    )

    with caplog.at_level("INFO"):
        report = await orchestrator.run_pipeline(job.id)

    assert not hasattr(report, "metadata")
    assert job_metadata_store.metadata_by_id[job.id]["domain"] == "computer_science"
    assert job_metadata_store.metadata_by_id[job.id]["format_label"] == "osint"
    assert job_metadata_store.metadata_by_id[job.id]["pipeline"]["current_phase"] == "synthesize"
    assert job_metadata_store.metadata_by_id[job.id]["active_sources"] == ["arxiv"]
    assert job_metadata_store.metadata_by_id[job.id]["query_refinements"] == [
        {
            "source": "arxiv",
            "raw_query": "threat actor report after:2022-01-01",
            "enriched_query": '"threat actor report after:2022-01-01" after:2022-01-01',
        }
    ]
    assert log == [
        ("agent_run", "threat actor report after:2022-01-01", True),
        ("chunk_search", job.id, "threat actor report after:2022-01-01", 10),
        ("synthesize", job.id, "threat actor report", 1, "standard"),
    ]
    assert report_metadata_store.metadata_by_id[report.id]["domain"] == "computer_science"
    assert report_metadata_store.metadata_by_id[report.id]["format_label"] == "osint"
    assert report_metadata_store.metadata_by_id[report.id]["pipeline"]["current_phase"] == "synthesize"


@pytest.mark.asyncio
async def test_run_pipeline_groups_final_success_writes_in_one_transaction(monkeypatch):
    fake_research_agent_module = types.ModuleType("src.meridian.infrastructure.llm.research_agent")
    fake_research_agent_module.ResearchAgent = object
    fake_synthesizer_module = types.ModuleType("src.meridian.infrastructure.llm.synthesizer")
    fake_synthesizer_module.ReportSynthesizer = object
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.llm.research_agent", fake_research_agent_module)
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.llm.synthesizer", fake_synthesizer_module)

    orchestrator_module = importlib.import_module("src.meridian.application.pipeline.orchestrator")
    PipelineOrchestrator = _orchestrator_factory(orchestrator_module.PipelineOrchestrator)

    job = ResearchJob(query="atomic success")
    document = Document(source="web", url="https://example.com", title="Atomic", content="content")
    chunk = Chunk(document_id=document.id, content="service chunk", credibility_score=0.87)
    transaction_manager = FakeTransactionManager()

    orchestrator = PipelineOrchestrator(
        job_repo=FakeJobRepo(job),
        report_repo=FakeReportRepo(),
        chunk_repo=FakeChunkRepo(),
        agent=FakeAgent([document]),
        synthesizer=FakeSynthesizer(),
        chunking_service=FakeChunkingService([chunk]),
        format_selector=FakeFormatSelector("general"),
        job_metadata_store=FakeWorkspaceMetadataStore(),
        report_metadata_store=FakeWorkspaceMetadataStore(),
        transaction_manager=transaction_manager,
    )

    await orchestrator.run_pipeline(job.id)

    assert transaction_manager.events == [
        "commit",
        "commit",
        "commit",
        "commit",
        "commit",
        "begin",
        ("end", None),
    ]


@pytest.mark.asyncio
async def test_run_pipeline_records_failure_in_single_transaction(monkeypatch):
    fake_research_agent_module = types.ModuleType("src.meridian.infrastructure.llm.research_agent")
    fake_research_agent_module.ResearchAgent = object
    fake_synthesizer_module = types.ModuleType("src.meridian.infrastructure.llm.synthesizer")
    fake_synthesizer_module.ReportSynthesizer = object
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.llm.research_agent", fake_research_agent_module)
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.llm.synthesizer", fake_synthesizer_module)

    orchestrator_module = importlib.import_module("src.meridian.application.pipeline.orchestrator")
    PipelineOrchestrator = _orchestrator_factory(orchestrator_module.PipelineOrchestrator)

    job = ResearchJob(query="atomic failure")
    document = Document(source="web", url="https://example.com", title="Atomic", content="content")
    chunk = Chunk(document_id=document.id, content="service chunk", credibility_score=0.87)
    job_repo = FakeJobRepo(job)
    transaction_manager = FakeTransactionManager()

    orchestrator = PipelineOrchestrator(
        job_repo=job_repo,
        report_repo=FailingReportRepo(),
        chunk_repo=FakeChunkRepo(),
        agent=FakeAgent([document]),
        synthesizer=FakeSynthesizer(),
        chunking_service=FakeChunkingService([chunk]),
        format_selector=FakeFormatSelector("general"),
        job_metadata_store=FakeWorkspaceMetadataStore(),
        report_metadata_store=FakeWorkspaceMetadataStore(),
        transaction_manager=transaction_manager,
    )

    await orchestrator.run_pipeline(job.id)

    assert job_repo.job.status == "failed"
    assert transaction_manager.events == [
        "commit",
        "commit",
        "commit",
        "commit",
        "commit",
        "begin",
        ("end", "RuntimeError"),
        "begin",
        ("end", None),
    ]


@pytest.mark.asyncio
async def test_run_pipeline_derives_query_refinements_from_execution_query_when_agent_records_none(monkeypatch):
    fake_research_agent_module = types.ModuleType("src.meridian.infrastructure.llm.research_agent")
    fake_research_agent_module.ResearchAgent = object
    fake_synthesizer_module = types.ModuleType("src.meridian.infrastructure.llm.synthesizer")
    fake_synthesizer_module.ReportSynthesizer = object
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.llm.research_agent", fake_research_agent_module)
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.llm.synthesizer", fake_synthesizer_module)

    orchestrator_module = importlib.import_module("src.meridian.application.pipeline.orchestrator")
    PipelineOrchestrator = _orchestrator_factory(orchestrator_module.PipelineOrchestrator)

    job = ResearchJob(query="threat actor report")
    document = Document(source="web", url="https://example.com", title="Threat Actor Report", content="content")
    chunk = Chunk(document_id=document.id, content="service chunk", credibility_score=0.87)
    job_repo = FakeJobRepo(job)
    report_repo = FakeReportRepo()
    chunk_repo = FakeChunkRepo()
    agent = FakeAgent([document])
    agent.query_refinements = []
    chunking_service = FakeChunkingService([chunk])
    synthesizer = FakeSynthesizer()
    format_selector = FakeFormatSelector("osint")
    job_metadata_store = FakeWorkspaceMetadataStore()
    report_metadata_store = FakeWorkspaceMetadataStore()
    job_metadata_store.metadata_by_id[job.id] = {
        "display_query": "threat actor report",
        "execution_query": "threat actor report after:2022-01-01",
    }

    orchestrator = PipelineOrchestrator(
        job_repo=job_repo,
        report_repo=report_repo,
        chunk_repo=chunk_repo,
        agent=agent,
        synthesizer=synthesizer,
        chunking_service=chunking_service,
        format_selector=format_selector,
        job_metadata_store=job_metadata_store,
        report_metadata_store=report_metadata_store,
    )

    report = await orchestrator.run_pipeline(job.id)

    assert report.query == "threat actor report"
    assert synthesizer.calls[0]["query"] == "threat actor report"
    assert chunk_repo.saved_chunks == [chunk]
    assert format_selector.calls == [("computer_science", "threat actor report after:2022-01-01")]
    assert job_metadata_store.metadata_by_id[job.id]["query_refinements"] == [
        {
            "source": "web",
            "raw_query": "threat actor report after:2022-01-01",
            "enriched_query": "threat actor report after:2022-01-01 -site:reddit.com -site:quora.com",
        }
    ]


@pytest.mark.asyncio
async def test_run_pipeline_passes_structured_advanced_options_to_agent_and_synthesizer(monkeypatch):
    fake_research_agent_module = types.ModuleType("src.meridian.infrastructure.llm.research_agent")
    fake_research_agent_module.ResearchAgent = object
    fake_synthesizer_module = types.ModuleType("src.meridian.infrastructure.llm.synthesizer")
    fake_synthesizer_module.ReportSynthesizer = object
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.llm.research_agent", fake_research_agent_module)
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.llm.synthesizer", fake_synthesizer_module)

    orchestrator_module = importlib.import_module("src.meridian.application.pipeline.orchestrator")
    PipelineOrchestrator = _orchestrator_factory(orchestrator_module.PipelineOrchestrator)

    job = ResearchJob(query="threat actor report")
    document = Document(source="web", url="https://example.com", title="Threat Actor Report", content="content")
    chunk = Chunk(document_id=document.id, content="service chunk", credibility_score=0.87)
    job_repo = FakeJobRepo(job)
    report_repo = FakeReportRepo()
    chunk_repo = FakeChunkRepo()
    agent = FakeAgent([document])
    chunking_service = FakeChunkingService([chunk])
    synthesizer = FakeSynthesizer()
    format_selector = FakeFormatSelector("osint")
    job_metadata_store = FakeWorkspaceMetadataStore()
    report_metadata_store = FakeWorkspaceMetadataStore()
    job_metadata_store.metadata_by_id[job.id] = {
        "display_query": "threat actor report",
        "execution_query": "threat actor report after:2022-01-01",
        "advanced_options": {
            "recentOnly": True,
            "requireMultipleSources": False,
            "reportDepth": "deep",
        },
    }

    orchestrator = PipelineOrchestrator(
        job_repo=job_repo,
        report_repo=report_repo,
        chunk_repo=chunk_repo,
        agent=agent,
        synthesizer=synthesizer,
        chunking_service=chunking_service,
        format_selector=format_selector,
        job_metadata_store=job_metadata_store,
        report_metadata_store=report_metadata_store,
    )

    await orchestrator.run_pipeline(job.id)

    assert agent.calls == [
        {
            "topic": "threat actor report after:2022-01-01",
            "max_iterations": 5,
            "require_multiple_sources": False,
        }
    ]
    assert synthesizer.calls[0]["query"] == "threat actor report"
    assert synthesizer.calls[0]["report_depth"] == "deep"


@pytest.mark.asyncio
async def test_run_pipeline_filters_evidence_before_chunking_and_persists_selection_metadata(monkeypatch):
    fake_research_agent_module = types.ModuleType("src.meridian.infrastructure.llm.research_agent")
    fake_research_agent_module.ResearchAgent = object
    fake_synthesizer_module = types.ModuleType("src.meridian.infrastructure.llm.synthesizer")
    fake_synthesizer_module.ReportSynthesizer = object
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.llm.research_agent", fake_research_agent_module)
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.llm.synthesizer", fake_synthesizer_module)

    orchestrator_module = importlib.import_module("src.meridian.application.pipeline.orchestrator")
    PipelineOrchestrator = _orchestrator_factory(orchestrator_module.PipelineOrchestrator)

    job = ResearchJob(query="AI regulation in EU")
    accepted = Document(source="semantic_scholar", url="https://example.com/accepted", title="AI regulation in EU", content="Accepted evidence")
    rejected = Document(source="arxiv", url="https://example.com/rejected", title="Solar imaging payload", content="Off topic evidence")
    accepted_decision = EvidenceDecision(
        document=accepted,
        reason="accepted",
        relevance_score=0.91,
        scorer_reason="llm_adjudicated",
        scorer_detail="aligned",
        adjudication_detail="aligned",
        source_query="AI regulation in EU",
        llm_attempted=True,
        llm_success=True,
    )
    rejected_decision = EvidenceDecision(
        document=rejected,
        reason="low_relevance",
        relevance_score=0.12,
        scorer_reason="lexical_mismatch",
        scorer_detail=None,
        adjudication_detail=None,
        source_query="AI regulation in EU",
    )
    selection_result = EvidenceSelectionResult(
        query=job.query,
        domain="general",
        source_queries={
            "semantic_scholar": ["AI regulation in EU"],
            "arxiv": ["AI regulation in EU", "AI regulation in EU after:2022-01-01"],
        },
        accepted=[accepted_decision],
        rejected=[rejected_decision],
        llm_budget_limit=5,
        llm_budget_used=1,
        llm_budget_remaining=4,
    )
    chunk = Chunk(document_id=accepted.id, content="service chunk", credibility_score=0.87)
    job_repo = FakeJobRepo(job)
    report_repo = FakeReportRepo()
    chunk_repo = FakeChunkRepo()
    agent = FakeAgent([accepted, rejected])
    agent.domain = "general"
    agent.query_refinements = [
        {
            "source": "semantic_scholar",
            "raw_query": "AI regulation in EU",
            "enriched_query": "AI regulation in EU",
        },
        {
            "source": "arxiv",
            "raw_query": "AI regulation in EU",
            "enriched_query": "AI regulation in EU after:2022-01-01",
        },
    ]
    chunking_service = FakeChunkingService([chunk])
    synthesizer = FakeSynthesizer()
    format_selector = FakeFormatSelector("general")
    job_metadata_store = FakeWorkspaceMetadataStore()
    report_metadata_store = FakeWorkspaceMetadataStore()

    orchestrator = PipelineOrchestrator(
        job_repo=job_repo,
        report_repo=report_repo,
        chunk_repo=chunk_repo,
        agent=agent,
        synthesizer=synthesizer,
        chunking_service=chunking_service,
        format_selector=format_selector,
        job_metadata_store=job_metadata_store,
        report_metadata_store=report_metadata_store,
        selection_service=FakeSelectionService(selection_result),
        coverage_gate=FakeCoverageGate(),
    )

    active_coverage_gate = orchestrator.coverage_gate
    await orchestrator.run_pipeline(job.id)

    assert chunking_service.calls == [[accepted]]
    assert job_metadata_store.metadata_by_id[job.id]["selection"]["accepted_count"] == 1
    assert job_metadata_store.metadata_by_id[job.id]["selection"]["rejected_count"] == 1
    assert job_metadata_store.metadata_by_id[job.id]["selection"]["source_queries"] == {
        "semantic_scholar": ["AI regulation in EU"],
        "arxiv": ["AI regulation in EU", "AI regulation in EU after:2022-01-01"],
    }
    assert job_metadata_store.metadata_by_id[job.id]["selection"]["accepted"][0]["credibility_score"] == 0.87
    assert job_metadata_store.metadata_by_id[job.id]["coverage"]["action"] == "synthesize"
    assert active_coverage_gate.calls[0]["source_distribution"] == {"semantic_scholar": 1}
    assert active_coverage_gate.calls[0]["query_family_distribution"] == {"semantic_scholar::AI regulation in EU": 1}


@pytest.mark.asyncio
async def test_run_pipeline_fails_when_coverage_is_insufficient(monkeypatch):
    fake_research_agent_module = types.ModuleType("src.meridian.infrastructure.llm.research_agent")
    fake_research_agent_module.ResearchAgent = object
    fake_synthesizer_module = types.ModuleType("src.meridian.infrastructure.llm.synthesizer")
    fake_synthesizer_module.ReportSynthesizer = object
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.llm.research_agent", fake_research_agent_module)
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.llm.synthesizer", fake_synthesizer_module)

    orchestrator_module = importlib.import_module("src.meridian.application.pipeline.orchestrator")
    PipelineOrchestrator = _orchestrator_factory(orchestrator_module.PipelineOrchestrator)

    job = ResearchJob(query="AI regulation in EU")
    document = Document(source="semantic_scholar", url="https://example.com/accepted", title="AI regulation in EU", content="Accepted evidence")
    accepted_decision = EvidenceDecision(
        document=document,
        reason="accepted",
        relevance_score=0.91,
        scorer_reason="llm_adjudicated",
        scorer_detail="aligned",
        adjudication_detail="aligned",
        source_query="AI regulation in EU",
        llm_attempted=True,
        llm_success=True,
    )
    selection_result = EvidenceSelectionResult(
        query=job.query,
        domain="general",
        source_queries={"semantic_scholar": ["AI regulation in EU"]},
        accepted=[accepted_decision],
        rejected=[],
        llm_budget_limit=5,
        llm_budget_used=1,
        llm_budget_remaining=4,
    )
    chunking_service = FakeChunkingService([])
    job_repo = FakeJobRepo(job)
    report_repo = FakeReportRepo()
    agent = FakeAgent([document])
    agent.domain = "general"
    job_metadata_store = FakeWorkspaceMetadataStore()
    report_metadata_store = FakeWorkspaceMetadataStore()
    coverage_gate = FakeCoverageGate(
        CoverageVerdict(
            domain="general",
            action="retry",
            reason="insufficient_documents",
            accepted_count=1,
            distinct_sources=1,
            average_relevance=0.91,
            source_distribution={"semantic_scholar": 1},
            query_family_distribution={"semantic_scholar::AI regulation in EU": 1},
            required_documents=2,
            required_sources=1,
            required_average_relevance=0.65,
        )
    )

    orchestrator = PipelineOrchestrator(
        job_repo=job_repo,
        report_repo=report_repo,
        chunk_repo=FakeChunkRepo(),
        agent=agent,
        synthesizer=FakeSynthesizer(),
        chunking_service=chunking_service,
        format_selector=FakeFormatSelector("general"),
        job_metadata_store=job_metadata_store,
        report_metadata_store=report_metadata_store,
        selection_service=FakeSelectionService(selection_result),
        coverage_gate=coverage_gate,
    )

    await orchestrator.run_pipeline(job.id)

    assert job_repo.job.status == "failed"
    assert "Insufficient relevant evidence" in job_repo.job.error_message
    assert chunking_service.calls == []
    assert job_metadata_store.metadata_by_id[job.id]["coverage"]["action"] == "retry"

