import asyncio

try:
    from celery.signals import worker_process_init
except ModuleNotFoundError:
    class _WorkerProcessInitStub:
        def connect(self, func):
            return func

    worker_process_init = _WorkerProcessInitStub()

from src.meridian.interfaces.workers.app import celery_app

_database_bootstrap_lock = asyncio.Lock()
_database_bootstrapped = False


async def ensure_database_bootstrapped() -> None:
    global _database_bootstrapped

    if _database_bootstrapped:
        return

    from src.meridian.infrastructure.database.session import init_db

    async with _database_bootstrap_lock:
        if _database_bootstrapped:
            return

        await init_db()
        _database_bootstrapped = True


@worker_process_init.connect
def _bootstrap_worker_process(**_kwargs):
    asyncio.run(ensure_database_bootstrapped())

async def _run_job_async(job_id: str):
    from src.meridian.application.pipeline.orchestrator import PipelineOrchestrator
    from src.meridian.application.pipeline.domain_classifier import DomainClassifier
    from src.meridian.application.pipeline.chunking import ChunkingService
    from src.meridian.application.pipeline.credibility_scorer import CredibilityScorer
    from src.meridian.application.pipeline.format_selector import FormatSelector
    from src.meridian.application.pipeline.query_processor import QueryProcessor
    from src.meridian.application.pipeline.source_router import SourceRouter
    from src.meridian.infrastructure.database.session import SessionLocal
    from src.meridian.infrastructure.database.sqlite_repositories import (
        SQLiteResearchJobRepository,
        SQLiteResearchReportRepository,
    )
    from src.meridian.infrastructure.external_apis.arxiv_client import ArXivClient
    from src.meridian.infrastructure.external_apis.ieee_client import IEEEClient
    from src.meridian.infrastructure.external_apis.pubmed_client import PubMedClient
    from src.meridian.infrastructure.external_apis.semantic_scholar_client import SemanticScholarClient
    from src.meridian.infrastructure.external_apis.web_search_client import WebSearchClient
    from src.meridian.infrastructure.external_apis.wikipedia_client import WikipediaClient
    from src.meridian.infrastructure.llm.openrouter_client import OpenRouterClient
    from src.meridian.infrastructure.llm.research_agent import ResearchAgent
    from src.meridian.infrastructure.llm.synthesizer import ReportSynthesizer
    from src.meridian.infrastructure.vector_store.chroma_repository import ChromaChunkRepository

    await ensure_database_bootstrapped()

    async with SessionLocal() as session:
        job_repo = SQLiteResearchJobRepository(session)
        report_repo = SQLiteResearchReportRepository(session)
        chunk_repo = ChromaChunkRepository()
        openrouter = OpenRouterClient()
        domain_classifier = DomainClassifier(openrouter)
        credibility_scorer = CredibilityScorer(openrouter)
        chunking_service = ChunkingService(credibility_scorer)
        format_selector = FormatSelector(openrouter)
        query_processor = QueryProcessor()
        source_router = SourceRouter()
        wikipedia_client = WikipediaClient()
        arxiv_client = ArXivClient()
        web_search_client = WebSearchClient()
        pubmed_client = PubMedClient()
        ieee_client = IEEEClient()
        semantic_scholar_client = SemanticScholarClient()
        agent = ResearchAgent(
            openrouter,
            domain_classifier=domain_classifier,
            source_router=source_router,
            wikipedia_client=wikipedia_client,
            arxiv_client=arxiv_client,
            web_search_client=web_search_client,
            pubmed_client=pubmed_client,
            ieee_client=ieee_client,
            semantic_scholar_client=semantic_scholar_client,
            query_processor=query_processor,
        )
        synthesizer = ReportSynthesizer(openrouter)

        orchestrator = PipelineOrchestrator(
            job_repo=job_repo,
            report_repo=report_repo,
            job_metadata_store=job_repo,
            report_metadata_store=report_repo,
            chunk_repo=chunk_repo,
            agent=agent,
            synthesizer=synthesizer,
            chunking_service=chunking_service,
            format_selector=format_selector,
            transaction_manager=session,
        )

        await orchestrator.run_pipeline(job_id)

@celery_app.task(name="run_research_pipeline")
def run_research_pipeline(job_id: str):
    asyncio.run(_run_job_async(job_id))
