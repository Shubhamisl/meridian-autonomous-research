import json
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from src.meridian.domain.entities import ResearchJob, ResearchReport
from src.meridian.domain.repositories import ResearchJobRepository, ResearchReportRepository
from src.meridian.infrastructure.database.models import DBResearchJob, DBResearchReport


def _attach_metadata(model: ResearchJob | ResearchReport, metadata: dict[str, Any]) -> ResearchJob | ResearchReport:
    if metadata:
        object.__setattr__(model, "metadata", metadata)
    return model


def _decode_metadata(raw_metadata: str | None) -> dict[str, Any]:
    if not raw_metadata:
        return {}
    try:
        decoded = json.loads(raw_metadata)
    except json.JSONDecodeError:
        return {}
    return decoded if isinstance(decoded, dict) else {}


def _encode_metadata(model: ResearchJob | ResearchReport) -> str | None:
    metadata = getattr(model, "metadata", None)
    if not metadata:
        return None
    return json.dumps(metadata)


async def _ensure_workspace_metadata_columns(session: AsyncSession) -> None:
    if session.info.get("workspace_metadata_columns_ready"):
        return

    table_columns = {
        "research_jobs": "workspace_metadata",
        "research_reports": "workspace_metadata",
    }
    altered = False

    for table_name, column_name in table_columns.items():
        result = await session.execute(text(f"PRAGMA table_info({table_name})"))
        existing_columns = {row[1] for row in result.all()}
        if column_name not in existing_columns:
            await session.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} TEXT"))
            altered = True

    if altered:
        await session.commit()

    session.info["workspace_metadata_columns_ready"] = True

class SQLiteResearchJobRepository(ResearchJobRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, job_id: str) -> Optional[ResearchJob]:
        await _ensure_workspace_metadata_columns(self.session)
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
        return _attach_metadata(job, _decode_metadata(db_job.workspace_metadata))

    async def save(self, job: ResearchJob) -> None:
        await _ensure_workspace_metadata_columns(self.session)
        db_job = await self.session.get(DBResearchJob, job.id)
        if db_job is None:
            db_job = DBResearchJob(id=job.id)

        db_job.user_id = job.user_id
        db_job.query = job.query
        db_job.status = job.status
        db_job.created_at = job.created_at
        db_job.completed_at = job.completed_at
        db_job.error_message = job.error_message
        db_job.workspace_metadata = _encode_metadata(job)

        self.session.add(db_job)
        await self.session.commit()

class SQLiteResearchReportRepository(ResearchReportRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_job_id(self, job_id: str) -> Optional[ResearchReport]:
        await _ensure_workspace_metadata_columns(self.session)
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
        return _attach_metadata(report, _decode_metadata(db_report.workspace_metadata))

    async def save(self, report: ResearchReport) -> None:
        await _ensure_workspace_metadata_columns(self.session)
        db_report = await self.session.get(DBResearchReport, report.id)
        if db_report is None:
            db_report = DBResearchReport(id=report.id)

        db_report.job_id = report.job_id
        db_report.query = report.query
        db_report.markdown_content = report.markdown_content
        db_report.created_at = report.created_at
        db_report.workspace_metadata = _encode_metadata(report)

        self.session.add(db_report)
        await self.session.commit()
