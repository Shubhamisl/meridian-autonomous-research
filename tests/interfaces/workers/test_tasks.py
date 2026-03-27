import sys
import types

import pytest

from src.meridian.domain.entities import Document
from src.meridian.interfaces.workers import tasks


class FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeRepo:
    def __init__(self, session):
        self.session = session


class FakeChunkRepo:
    pass


class FakeOpenRouterClient:
    pass


class FakeClassifier:
    def __init__(self, openrouter_client):
        self.openrouter_client = openrouter_client


class FakeRouter:
    def __init__(self):
        self.calls = []

    def get_tools_for_domain(self, domain):
        self.calls.append(domain)
        return [{"type": "function", "function": {"name": "search_pubmed", "parameters": {"type": "object"}}}]


class FakeSourceClient:
    pass


class FakeResearchAgent:
    instances = []

    def __init__(
        self,
        openrouter_client,
        domain_classifier=None,
        source_router=None,
        wikipedia_client=None,
        arxiv_client=None,
        web_search_client=None,
        pubmed_client=None,
        ieee_client=None,
        semantic_scholar_client=None,
    ):
        self.openrouter_client = openrouter_client
        self.domain_classifier = domain_classifier
        self.source_router = source_router
        self.wikipedia_client = wikipedia_client
        self.arxiv_client = arxiv_client
        self.web_search_client = web_search_client
        self.pubmed_client = pubmed_client
        self.ieee_client = ieee_client
        self.semantic_scholar_client = semantic_scholar_client
        self.__class__.instances.append(self)

    async def run(self, topic, max_iterations=5):
        return [Document(source="pubmed", title="PubMed", content="content", url="https://pubmed.ncbi.nlm.nih.gov/12345/")]


class FakeSynthesizer:
    def __init__(self, openrouter_client):
        self.openrouter_client = openrouter_client


class FakeOrchestrator:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.run_calls = []
        self.__class__.instances.append(self)

    async def run_pipeline(self, job_id):
        self.run_calls.append(job_id)


@pytest.mark.asyncio
async def test_run_job_async_wires_phase_a_dependencies(monkeypatch):
    FakeOrchestrator.instances.clear()
    FakeResearchAgent.instances.clear()
    fake_session = FakeSession()
    fake_router = FakeRouter()
    fake_chroma_module = types.ModuleType("src.meridian.infrastructure.vector_store.chroma_repository")
    fake_chroma_module.ChromaChunkRepository = FakeChunkRepo
    fake_wikipedia_module = types.ModuleType("src.meridian.infrastructure.external_apis.wikipedia_client")
    fake_wikipedia_module.WikipediaClient = FakeSourceClient
    fake_arxiv_module = types.ModuleType("src.meridian.infrastructure.external_apis.arxiv_client")
    fake_arxiv_module.ArXivClient = FakeSourceClient
    fake_web_search_module = types.ModuleType("src.meridian.infrastructure.external_apis.web_search_client")
    fake_web_search_module.WebSearchClient = FakeSourceClient
    fake_pubmed_module = types.ModuleType("src.meridian.infrastructure.external_apis.pubmed_client")
    fake_pubmed_module.PubMedClient = FakeSourceClient
    fake_ieee_module = types.ModuleType("src.meridian.infrastructure.external_apis.ieee_client")
    fake_ieee_module.IEEEClient = FakeSourceClient
    fake_semantic_scholar_module = types.ModuleType("src.meridian.infrastructure.external_apis.semantic_scholar_client")
    fake_semantic_scholar_module.SemanticScholarClient = FakeSourceClient
    fake_research_agent_module = types.ModuleType("src.meridian.infrastructure.llm.research_agent")
    fake_research_agent_module.ResearchAgent = FakeResearchAgent
    fake_synthesizer_module = types.ModuleType("src.meridian.infrastructure.llm.synthesizer")
    fake_synthesizer_module.ReportSynthesizer = FakeSynthesizer

    monkeypatch.setattr("src.meridian.infrastructure.database.session.SessionLocal", lambda: fake_session)
    monkeypatch.setattr("src.meridian.infrastructure.database.sqlite_repositories.SQLiteResearchJobRepository", FakeRepo)
    monkeypatch.setattr("src.meridian.infrastructure.database.sqlite_repositories.SQLiteResearchReportRepository", FakeRepo)
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.vector_store.chroma_repository", fake_chroma_module)
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.external_apis.wikipedia_client", fake_wikipedia_module)
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.external_apis.arxiv_client", fake_arxiv_module)
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.external_apis.web_search_client", fake_web_search_module)
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.external_apis.pubmed_client", fake_pubmed_module)
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.external_apis.ieee_client", fake_ieee_module)
    monkeypatch.setitem(
        sys.modules,
        "src.meridian.infrastructure.external_apis.semantic_scholar_client",
        fake_semantic_scholar_module,
    )
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.llm.research_agent", fake_research_agent_module)
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.llm.synthesizer", fake_synthesizer_module)
    monkeypatch.setattr("src.meridian.infrastructure.llm.openrouter_client.OpenRouterClient", FakeOpenRouterClient)
    monkeypatch.setattr("src.meridian.application.pipeline.domain_classifier.DomainClassifier", FakeClassifier)
    monkeypatch.setattr("src.meridian.application.pipeline.source_router.SourceRouter", lambda: fake_router)
    monkeypatch.setattr("src.meridian.application.pipeline.orchestrator.PipelineOrchestrator", FakeOrchestrator)

    await tasks._run_job_async("job-123")

    orchestrator = FakeOrchestrator.instances[0]
    agent = orchestrator.kwargs["agent"]
    assert agent.domain_classifier.openrouter_client.__class__ is FakeOpenRouterClient
    assert agent.source_router is fake_router
    assert agent.pubmed_client.__class__ is FakeSourceClient
    assert agent.ieee_client.__class__ is FakeSourceClient
    assert agent.semantic_scholar_client.__class__ is FakeSourceClient
    assert len(FakeResearchAgent.instances) == 1
    assert orchestrator.kwargs["synthesizer"].openrouter_client.__class__ is FakeOpenRouterClient
