from src.meridian.domain.repositories import ResearchJobRepository, ResearchReportRepository, ChunkRepository
from src.meridian.infrastructure.llm.research_agent import ResearchAgent
from src.meridian.infrastructure.llm.synthesizer import ReportSynthesizer
from src.meridian.application.pipeline.chunking import chunk_document

class PipelineOrchestrator:
    def __init__(
        self,
        job_repo: ResearchJobRepository,
        report_repo: ResearchReportRepository,
        chunk_repo: ChunkRepository,
        agent: ResearchAgent,
        synthesizer: ReportSynthesizer
    ):
        self.job_repo = job_repo
        self.report_repo = report_repo
        self.chunk_repo = chunk_repo
        self.agent = agent
        self.synthesizer = synthesizer

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
            all_chunks = []
            for doc in documents:
                chunks = chunk_document(doc)
                all_chunks.extend(chunks)

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
