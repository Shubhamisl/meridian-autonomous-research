import sqlite3
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.meridian.domain.entities import ResearchJob, ResearchReport
from src.meridian.infrastructure.database.session import init_db
from src.meridian.infrastructure.database.sqlite_repositories import (
    SQLiteResearchJobRepository,
    SQLiteResearchReportRepository,
)


def _create_legacy_schema(db_path: Path) -> None:
    connection = sqlite3.connect(db_path)
    try:
        connection.execute(
            """
            CREATE TABLE research_jobs (
                id VARCHAR PRIMARY KEY,
                user_id VARCHAR,
                query VARCHAR NOT NULL,
                status VARCHAR NOT NULL,
                created_at DATETIME NOT NULL,
                completed_at DATETIME,
                error_message TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE research_reports (
                id VARCHAR PRIMARY KEY,
                job_id VARCHAR NOT NULL,
                query VARCHAR NOT NULL,
                markdown_content TEXT NOT NULL,
                created_at DATETIME NOT NULL
            )
            """
        )
        connection.commit()
    finally:
        connection.close()


@pytest.mark.asyncio
async def test_init_db_adds_workspace_metadata_columns_and_repositories_use_them(tmp_path: Path):
    db_path = tmp_path / "legacy-research.db"
    _create_legacy_schema(db_path)

    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = async_sessionmaker(bind=engine, autoflush=False, autocommit=False)

    try:
        await init_db(engine)

        async with engine.connect() as conn:
            job_columns = {row[1] for row in (await conn.execute(text("PRAGMA table_info(research_jobs)"))).all()}
            report_columns = {row[1] for row in (await conn.execute(text("PRAGMA table_info(research_reports)"))).all()}

        assert "workspace_metadata" in job_columns
        assert "workspace_metadata" in report_columns

        async with session_factory() as session:
            job_repo = SQLiteResearchJobRepository(session)
            report_repo = SQLiteResearchReportRepository(session)
            created_at = datetime(2024, 1, 1, 0, 0, 0)

            job = ResearchJob(
                id="job-123",
                user_id="user-123",
                query="threat actor report",
                status="pending",
                created_at=created_at,
            )
            report = ResearchReport(
                id="report-123",
                job_id="job-123",
                query="threat actor report",
                markdown_content="# Threat Actor Report",
                created_at=created_at,
            )

            await job_repo.save(job)
            await job_repo.save_workspace_metadata(job.id, {"domain": "computer_science", "pipeline": {"current_phase": "research"}})
            await report_repo.save(report)
            await report_repo.save_workspace_metadata(report.id, {"format_label": "osint"})
            await session.commit()

            reloaded_job = await job_repo.get(job.id)
            reloaded_report = await report_repo.get_by_job_id(job.id)

            assert reloaded_job is not None
            assert reloaded_report is not None
            assert not hasattr(reloaded_job, "metadata")
            assert not hasattr(reloaded_report, "metadata")
            assert await job_repo.get_workspace_metadata(job.id) == {
                "domain": "computer_science",
                "pipeline": {"current_phase": "research"},
            }
            assert await report_repo.get_workspace_metadata(report.id) == {"format_label": "osint"}
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_repository_save_requires_explicit_commit_for_cross_session_visibility(tmp_path: Path):
    db_path = tmp_path / "repository-transactionality.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = async_sessionmaker(bind=engine, autoflush=False, autocommit=False)

    try:
        await init_db(engine)
        created_at = datetime(2024, 1, 1, 0, 0, 0)

        async with session_factory() as writer_session:
            job_repo = SQLiteResearchJobRepository(writer_session)
            job = ResearchJob(
                id="job-tx",
                user_id="user-123",
                query="transactionality check",
                status="pending",
                created_at=created_at,
            )
            await job_repo.save(job)

            async with session_factory() as reader_session:
                reader_repo = SQLiteResearchJobRepository(reader_session)
                assert await reader_repo.get(job.id) is None

            await writer_session.commit()

        async with session_factory() as reader_session:
            reader_repo = SQLiteResearchJobRepository(reader_session)
            reloaded_job = await reader_repo.get("job-tx")

        assert reloaded_job is not None
        assert reloaded_job.query == "transactionality check"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_init_db_bootstrap_cache_is_per_engine_instance() -> None:
    first_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    second_engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    try:
        await init_db(first_engine)
        await init_db(second_engine)

        async with second_engine.connect() as conn:
            result = await conn.execute(text("PRAGMA table_info(research_jobs)"))
            columns = {row[1] for row in result.all()}

        assert "id" in columns
        assert "workspace_metadata" in columns
    finally:
        await first_engine.dispose()
        await second_engine.dispose()
