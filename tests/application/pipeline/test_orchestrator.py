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


class FakeChunkRepo:
    def __init__(self):
        self.saved_chunks = []

    async def save_all(self, job_id, chunks):
        self.saved_chunks = list(chunks)

    async def search(self, job_id, query, top_k=5):
        return []


class FakeAgent:
    def __init__(self, documents):
        self.documents = documents
        self.calls = []
        self.domain = "computer_science"

    async def run(self, topic, max_iterations=5):
        self.calls.append(topic)
        return self.documents


class FakeSynthesizer:
    def __init__(self):
        self.calls = []

    async def synthesize(self, job_id, query, chunks, format_label):
        self.calls.append(
            {
                "job_id": job_id,
                "query": query,
                "chunks": chunks,
                "format_label": format_label,
            }
        )
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
    chunking_service = FakeChunkingService([chunk])
    synthesizer = FakeSynthesizer()
    format_selector = FakeFormatSelector("osint")

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

    orchestrator = PipelineOrchestrator(
        job_repo=job_repo,
        report_repo=report_repo,
        chunk_repo=chunk_repo,
        agent=agent,
        synthesizer=synthesizer,
        chunking_service=chunking_service,
        format_selector=format_selector,
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

    orchestrator = PipelineOrchestrator(
        job_repo=job_repo,
        report_repo=report_repo,
        chunk_repo=chunk_repo,
        agent=agent,
        synthesizer=synthesizer,
        chunking_service=chunking_service,
        format_selector=format_selector,
    )

    await orchestrator.run_pipeline(job.id)

    assert format_selector.calls == [("general", job.query)]


@pytest.mark.asyncio
async def test_run_pipeline_logs_and_persists_workspace_metadata(monkeypatch, caplog):
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
    job_repo = FakeJobRepo(job)
    report_repo = FakeReportRepo()
    chunk_repo = FakeChunkRepo()
    agent = FakeAgent([document])
    chunking_service = FakeChunkingService([chunk])
    synthesizer = FakeSynthesizer()
    format_selector = FakeFormatSelector("osint")

    orchestrator = PipelineOrchestrator(
        job_repo=job_repo,
        report_repo=report_repo,
        chunk_repo=chunk_repo,
        agent=agent,
        synthesizer=synthesizer,
        chunking_service=chunking_service,
        format_selector=format_selector,
    )

    with caplog.at_level("INFO"):
        report = await orchestrator.run_pipeline(job.id)

    assert report.metadata["domain"] == "computer_science"
    assert report.metadata["format_label"] == "osint"
    assert report.metadata["pipeline"]["current_phase"] == "synthesize"
    assert report.metadata["active_sources"] == ["arxiv"]
    assert report.metadata["query_refinements"] == []
