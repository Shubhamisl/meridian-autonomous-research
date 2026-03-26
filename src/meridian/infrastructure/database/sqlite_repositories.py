from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.meridian.domain.entities import ResearchJob, ResearchReport
from src.meridian.domain.repositories import ResearchJobRepository, ResearchReportRepository
from src.meridian.infrastructure.database.models import DBResearchJob, DBResearchReport

class SQLiteResearchJobRepository(ResearchJobRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, job_id: str) -> Optional[ResearchJob]:
        stmt = select(DBResearchJob).where(DBResearchJob.id == job_id)
        result = await self.session.execute(stmt)
        db_job = result.scalar_one_or_none()
        if not db_job:
            return None
        return ResearchJob(
            id=db_job.id,
            query=db_job.query,
            status=db_job.status,
            created_at=db_job.created_at,
            completed_at=db_job.completed_at,
            error_message=db_job.error_message
        )

    async def save(self, job: ResearchJob) -> None:
        db_job = DBResearchJob(
            id=job.id,
            query=job.query,
            status=job.status,
            created_at=job.created_at,
            completed_at=job.completed_at,
            error_message=job.error_message
        )
        await self.session.merge(db_job)
        await self.session.commit()

class SQLiteResearchReportRepository(ResearchReportRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_job_id(self, job_id: str) -> Optional[ResearchReport]:
        stmt = select(DBResearchReport).where(DBResearchReport.job_id == job_id)
        result = await self.session.execute(stmt)
        db_report = result.scalar_one_or_none()
        if not db_report:
            return None
        return ResearchReport(
            id=db_report.id,
            job_id=db_report.job_id,
            query=db_report.query,
            markdown_content=db_report.markdown_content,
            created_at=db_report.created_at
        )

    async def save(self, report: ResearchReport) -> None:
        db_report = DBResearchReport(
            id=report.id,
            job_id=report.job_id,
            query=report.query,
            markdown_content=report.markdown_content,
            created_at=report.created_at
        )
        await self.session.merge(db_report)
        await self.session.commit()
