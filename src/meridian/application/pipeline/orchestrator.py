import logging

from src.meridian.domain.repositories import ResearchJobRepository, ResearchReportRepository, ChunkRepository
from src.meridian.infrastructure.llm.research_agent import ResearchAgent
from src.meridian.infrastructure.llm.synthesizer import ReportSynthesizer
from src.meridian.application.pipeline.chunking import ChunkingService

logger = logging.getLogger(__name__)

class PipelineOrchestrator:
    def __init__(
        self,
        job_repo: ResearchJobRepository,
        report_repo: ResearchReportRepository,
        chunk_repo: ChunkRepository,
        agent: ResearchAgent,
        synthesizer: ReportSynthesizer,
        chunking_service: ChunkingService,
    ):
        self.job_repo = job_repo
        self.report_repo = report_repo
        self.chunk_repo = chunk_repo
        self.agent = agent
        self.synthesizer = synthesizer
        self.chunking_service = chunking_service

    async def run_pipeline(self, job_id: str):
        job = await self.job_repo.get(job_id)
        if not job:
            return

        try:
            job = job.start()
            await self.job_repo.save(job)

            # Phase 1: Research Agent loop
            documents = await self.agent.run(topic=job.query)

            # Phase 2: Chunk & Embed
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

            # Phase 3 & 4: RAG Retrieval and Synthesis
            retrieved_chunks = await self.chunk_repo.search(job_id, query=job.query, top_k=10)
            
            if not retrieved_chunks:
                retrieved_chunks = all_chunks[:10]

            report = await self.synthesizer.synthesize(job_id, job.query, retrieved_chunks)

            await self.report_repo.save(report)
            
            job = job.complete()
            await self.job_repo.save(job)

        except Exception as e:
            job = job.fail(error_message=str(e))
            await self.job_repo.save(job)
