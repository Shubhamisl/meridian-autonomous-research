import importlib
import sys
import types

import pytest

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

    async def run(self, topic, max_iterations=5):
        self.calls.append(topic)
        if self.log is not None:
            self.log.append(("agent_run", topic))
        return self.documents


class FakeSynthesizer:
    def __init__(self, log=None):
        self.calls = []
        self.log = log

    async def synthesize(self, job_id, query, chunks, format_label):
        self.calls.append(
            {
                "job_id": job_id,
                "query": query,
                "chunks": chunks,
                "format_label": format_label,
            }
        )
        if self.log is not None:
            self.log.append(("synthesize", job_id, query, len(chunks)))
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


@pytest.mark.asyncio
async def test_run_pipeline_uses_chunking_service_logs_document_summary_and_passes_format_label(monkeypatch, caplog):
    fake_research_agent_module = types.ModuleType("src.meridian.infrastructure.llm.research_agent")
    fake_research_agent_module.ResearchAgent = object
    fake_synthesizer_module = types.ModuleType("src.meridian.infrastructure.llm.synthesizer")
    fake_synthesizer_module.ReportSynthesizer = object
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.llm.research_agent", fake_research_agent_module)
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.llm.synthesizer", fake_synthesizer_module)

    orchestrator_module = importlib.import_module("src.meridian.application.pipeline.orchestrator")
    PipelineOrchestrator = orchestrator_module.PipelineOrchestrator

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
    PipelineOrchestrator = orchestrator_module.PipelineOrchestrator

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
    PipelineOrchestrator = orchestrator_module.PipelineOrchestrator

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
    PipelineOrchestrator = orchestrator_module.PipelineOrchestrator

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
            "raw_query": "threat actor report",
            "enriched_query": '"threat actor report" after:2022-01-01',
        }
    ]
    assert log == [
        ("agent_run", "threat actor report after:2022-01-01"),
        ("chunk_search", job.id, "threat actor report after:2022-01-01", 10),
        ("synthesize", job.id, "threat actor report", 1),
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
    PipelineOrchestrator = orchestrator_module.PipelineOrchestrator

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
    PipelineOrchestrator = orchestrator_module.PipelineOrchestrator

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
        "begin",
        ("end", "RuntimeError"),
        "begin",
        ("end", None),
    ]
