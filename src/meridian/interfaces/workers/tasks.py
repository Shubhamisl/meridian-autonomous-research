import asyncio
from src.meridian.interfaces.workers.app import celery_app

async def _run_job_async(job_id: str):
    from src.meridian.application.pipeline.orchestrator import PipelineOrchestrator
    from src.meridian.infrastructure.database.session import SessionLocal
    from src.meridian.infrastructure.database.sqlite_repositories import (
        SQLiteResearchJobRepository,
        SQLiteResearchReportRepository,
    )
    from src.meridian.infrastructure.llm.openrouter_client import OpenRouterClient
    from src.meridian.infrastructure.llm.research_agent import ResearchAgent
    from src.meridian.infrastructure.llm.synthesizer import ReportSynthesizer
    from src.meridian.infrastructure.vector_store.chroma_repository import ChromaChunkRepository

    async with SessionLocal() as session:
        job_repo = SQLiteResearchJobRepository(session)
        report_repo = SQLiteResearchReportRepository(session)
        chunk_repo = ChromaChunkRepository()
        openrouter = OpenRouterClient()
        agent = ResearchAgent(openrouter)
        synthesizer = ReportSynthesizer(openrouter)

        orchestrator = PipelineOrchestrator(
            job_repo=job_repo,
            report_repo=report_repo,
            chunk_repo=chunk_repo,
            agent=agent,
            synthesizer=synthesizer
        )

        await orchestrator.run_pipeline(job_id)

@celery_app.task(name="run_research_pipeline")
def run_research_pipeline(job_id: str):
    asyncio.run(_run_job_async(job_id))
