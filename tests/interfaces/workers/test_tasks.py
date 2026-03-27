import sys
import types

import pytest

from src.meridian.domain.entities import Document
from src.meridian.interfaces.workers import tasks


class FakeSession:
    def __init__(self, events=None):
        self.events = events if events is not None else []

    async def __aenter__(self):
        self.events.append("session_enter")
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeRepo:
    def __init__(self, session):
        self.session = session

    async def get_workspace_metadata(self, entity_id):
        return {}

    async def save_workspace_metadata(self, entity_id, metadata):
        return None


class FakeChunkRepo:
    pass


class FakeOpenRouterClient:
    pass


class FakeClassifier:
    def __init__(self, openrouter_client):
        self.openrouter_client = openrouter_client


class FakeCredibilityScorer:
    instances = []

    def __init__(self, openrouter_client):
        self.openrouter_client = openrouter_client
        self.__class__.instances.append(self)


class FakeChunkingService:
    instances = []

    def __init__(self, credibility_scorer):
        self.credibility_scorer = credibility_scorer
        self.__class__.instances.append(self)


class FakeFormatSelector:
    instances = []

    def __init__(self, openrouter_client):
        self.openrouter_client = openrouter_client
        self.__class__.instances.append(self)


class FakeQueryProcessor:
    instances = []

    def __init__(self):
        self.__class__.instances.append(self)


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
        query_processor=None,
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
        self.query_processor = query_processor
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
async def test_run_job_async_runs_init_db_before_wiring_dependencies(monkeypatch):
    FakeOrchestrator.instances.clear()
    FakeResearchAgent.instances.clear()
    FakeCredibilityScorer.instances.clear()
    FakeChunkingService.instances.clear()
    FakeFormatSelector.instances.clear()
    FakeQueryProcessor.instances.clear()
    events = []
    fake_session = FakeSession(events)
    fake_router = FakeRouter()
    fake_session_module = types.ModuleType("src.meridian.infrastructure.database.session")
    fake_session_module.SessionLocal = lambda: fake_session

    async def fake_init_db():
        events.append("init_db")

    fake_session_module.init_db = fake_init_db
    fake_repositories_module = types.ModuleType("src.meridian.infrastructure.database.sqlite_repositories")
    fake_repositories_module.SQLiteResearchJobRepository = FakeRepo
    fake_repositories_module.SQLiteResearchReportRepository = FakeRepo
    fake_chunking_module = types.ModuleType("src.meridian.application.pipeline.chunking")
    fake_chunking_module.ChunkingService = FakeChunkingService
    fake_domain_classifier_module = types.ModuleType("src.meridian.application.pipeline.domain_classifier")
    fake_domain_classifier_module.DomainClassifier = FakeClassifier
    fake_credibility_module = types.ModuleType("src.meridian.application.pipeline.credibility_scorer")
    fake_credibility_module.CredibilityScorer = FakeCredibilityScorer
    fake_format_selector_module = types.ModuleType("src.meridian.application.pipeline.format_selector")
    fake_format_selector_module.FormatSelector = FakeFormatSelector
    fake_source_router_module = types.ModuleType("src.meridian.application.pipeline.source_router")
    fake_source_router_module.SourceRouter = lambda: fake_router
    fake_query_processor_module = types.ModuleType("src.meridian.application.pipeline.query_processor")
    fake_query_processor_module.QueryProcessor = FakeQueryProcessor
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
    fake_openrouter_module = types.ModuleType("src.meridian.infrastructure.llm.openrouter_client")
    fake_openrouter_module.OpenRouterClient = FakeOpenRouterClient
    fake_research_agent_module = types.ModuleType("src.meridian.infrastructure.llm.research_agent")
    fake_research_agent_module.ResearchAgent = FakeResearchAgent
    fake_synthesizer_module = types.ModuleType("src.meridian.infrastructure.llm.synthesizer")
    fake_synthesizer_module.ReportSynthesizer = FakeSynthesizer
    fake_orchestrator_module = types.ModuleType("src.meridian.application.pipeline.orchestrator")
    fake_orchestrator_module.PipelineOrchestrator = FakeOrchestrator

    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.database.session", fake_session_module)
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.database.sqlite_repositories", fake_repositories_module)
    monkeypatch.setitem(sys.modules, "src.meridian.application.pipeline.chunking", fake_chunking_module)
    monkeypatch.setitem(sys.modules, "src.meridian.application.pipeline.domain_classifier", fake_domain_classifier_module)
    monkeypatch.setitem(sys.modules, "src.meridian.application.pipeline.credibility_scorer", fake_credibility_module)
    monkeypatch.setitem(sys.modules, "src.meridian.application.pipeline.format_selector", fake_format_selector_module)
    monkeypatch.setitem(sys.modules, "src.meridian.application.pipeline.source_router", fake_source_router_module)
    monkeypatch.setitem(sys.modules, "src.meridian.application.pipeline.query_processor", fake_query_processor_module)
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
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.llm.openrouter_client", fake_openrouter_module)
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.llm.research_agent", fake_research_agent_module)
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.llm.synthesizer", fake_synthesizer_module)
    monkeypatch.setitem(sys.modules, "src.meridian.application.pipeline.orchestrator", fake_orchestrator_module)
    monkeypatch.setattr(tasks, "_database_bootstrapped", False)

    await tasks._run_job_async("job-123")

    assert events[:2] == ["init_db", "session_enter"]
    orchestrator = FakeOrchestrator.instances[0]
    agent = orchestrator.kwargs["agent"]
    chunking_service = orchestrator.kwargs["chunking_service"]
    credibility_scorer = chunking_service.credibility_scorer
    format_selector = orchestrator.kwargs["format_selector"]
    assert agent.domain_classifier.openrouter_client.__class__ is FakeOpenRouterClient
    assert agent.source_router is fake_router
    assert agent.pubmed_client.__class__ is FakeSourceClient
    assert agent.ieee_client.__class__ is FakeSourceClient
    assert agent.semantic_scholar_client.__class__ is FakeSourceClient
    assert len(FakeResearchAgent.instances) == 1
    assert orchestrator.kwargs["synthesizer"].openrouter_client.__class__ is FakeOpenRouterClient
    assert len(FakeCredibilityScorer.instances) == 1
    assert len(FakeChunkingService.instances) == 1
    assert len(FakeFormatSelector.instances) == 1
    assert len(FakeQueryProcessor.instances) == 1
    assert credibility_scorer is FakeCredibilityScorer.instances[0]
    assert chunking_service is FakeChunkingService.instances[0]
    assert credibility_scorer.openrouter_client.__class__ is FakeOpenRouterClient
    assert format_selector is FakeFormatSelector.instances[0]
    assert format_selector.openrouter_client.__class__ is FakeOpenRouterClient
    assert agent.query_processor is FakeQueryProcessor.instances[0]
    assert orchestrator.kwargs["job_metadata_store"].__class__ is FakeRepo
    assert orchestrator.kwargs["report_metadata_store"].__class__ is FakeRepo
    assert orchestrator.kwargs["transaction_manager"] is fake_session


@pytest.mark.asyncio
async def test_ensure_database_bootstrapped_only_initializes_once(monkeypatch):
    events = []
    fake_session_module = types.ModuleType("src.meridian.infrastructure.database.session")

    async def fake_init_db():
        events.append("init_db")

    fake_session_module.init_db = fake_init_db
    monkeypatch.setitem(sys.modules, "src.meridian.infrastructure.database.session", fake_session_module)
    monkeypatch.setattr(tasks, "_database_bootstrapped", False)

    await tasks.ensure_database_bootstrapped()
    await tasks.ensure_database_bootstrapped()

    assert events == ["init_db"]
