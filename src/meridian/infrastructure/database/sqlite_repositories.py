import json
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.meridian.domain.entities import ResearchJob, ResearchReport
from src.meridian.domain.repositories import ResearchJobRepository, ResearchReportRepository
from src.meridian.infrastructure.database.models import DBResearchJob, DBResearchReport


def _decode_metadata(raw_metadata: str | None) -> dict[str, Any]:
    if not raw_metadata:
        return {}
    try:
        decoded = json.loads(raw_metadata)
    except json.JSONDecodeError:
        return {}
    return decoded if isinstance(decoded, dict) else {}


def _encode_metadata(metadata: dict[str, Any]) -> str | None:
    if not metadata:
        return None
    return json.dumps(metadata)

class SQLiteResearchJobRepository(ResearchJobRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, job_id: str) -> Optional[ResearchJob]:
        stmt = select(DBResearchJob).where(DBResearchJob.id == job_id)
        result = await self.session.execute(stmt)
        db_job = result.scalar_one_or_none()
        if not db_job:
            return None
        job = ResearchJob(
            id=db_job.id,
            query=db_job.query,
            user_id=db_job.user_id,
            status=db_job.status,
            created_at=db_job.created_at,
            completed_at=db_job.completed_at,
            error_message=db_job.error_message
        )
        return job

    async def save(self, job: ResearchJob) -> None:
        db_job = await self.session.get(DBResearchJob, job.id)
        if db_job is None:
            db_job = DBResearchJob(id=job.id)

        db_job.user_id = job.user_id
        db_job.query = job.query
        db_job.status = job.status
        db_job.created_at = job.created_at
        db_job.completed_at = job.completed_at
        db_job.error_message = job.error_message

        self.session.add(db_job)
        await self.session.flush()

    async def get_workspace_metadata(self, job_id: str) -> dict[str, Any]:
        db_job = await self.session.get(DBResearchJob, job_id)
        if db_job is None:
            return {}
        return _decode_metadata(db_job.workspace_metadata)

    async def save_workspace_metadata(self, job_id: str, metadata: dict[str, Any]) -> None:
        db_job = await self.session.get(DBResearchJob, job_id)
        if db_job is None:
            raise ValueError(f"Research job {job_id} not found")
        db_job.workspace_metadata = _encode_metadata(metadata)
        self.session.add(db_job)
        await self.session.flush()

class SQLiteResearchReportRepository(ResearchReportRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_job_id(self, job_id: str) -> Optional[ResearchReport]:
        stmt = select(DBResearchReport).where(DBResearchReport.job_id == job_id)
        result = await self.session.execute(stmt)
        db_report = result.scalar_one_or_none()
        if not db_report:
            return None
        report = ResearchReport(
            id=db_report.id,
            job_id=db_report.job_id,
            query=db_report.query,
            markdown_content=db_report.markdown_content,
            created_at=db_report.created_at
        )
        return report

    async def save(self, report: ResearchReport) -> None:
        db_report = await self.session.get(DBResearchReport, report.id)
        if db_report is None:
            db_report = DBResearchReport(id=report.id)

        db_report.job_id = report.job_id
        db_report.query = report.query
        db_report.markdown_content = report.markdown_content
        db_report.created_at = report.created_at

        self.session.add(db_report)
        await self.session.flush()

    async def get_workspace_metadata(self, report_id: str) -> dict[str, Any]:
        db_report = await self.session.get(DBResearchReport, report_id)
        if db_report is None:
            return {}
        return _decode_metadata(db_report.workspace_metadata)

    async def save_workspace_metadata(self, report_id: str, metadata: dict[str, Any]) -> None:
        db_report = await self.session.get(DBResearchReport, report_id)
        if db_report is None:
            raise ValueError(f"Research report {report_id} not found")
        db_report.workspace_metadata = _encode_metadata(metadata)
        self.session.add(db_report)
        await self.session.flush()
