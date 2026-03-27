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

    async def run(self, topic, max_iterations=5):
        self.calls.append(topic)
        return self.documents


class FakeSynthesizer:
    async def synthesize(self, job_id, query, chunks):
        return ResearchReport(job_id=job_id, query=query, markdown_content="report")


class FakeChunkingService:
    def __init__(self, chunks):
        self.chunks = chunks
        self.calls = []

    async def chunk_documents(self, documents):
        self.calls.append(list(documents))
        return self.chunks


@pytest.mark.asyncio
async def test_run_pipeline_uses_chunking_service_and_logs_document_summary(monkeypatch, caplog):
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
    )

    with caplog.at_level("INFO"):
        await orchestrator.run_pipeline(job.id)

    assert len(chunking_service.calls) == 1
    assert chunking_service.calls[0] == [document]
    assert chunk_repo.saved_chunks == [chunk]
    assert len(report_repo.saved_reports) == 1
    assert [
        record.message
        for record in caplog.records
        if record.levelname == "INFO"
    ] == [
        f"Chunked document summary: source=web title={'T' * 60} credibility_score=0.87"
    ]
