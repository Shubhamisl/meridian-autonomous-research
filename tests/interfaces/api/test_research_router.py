import json
from datetime import datetime
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.meridian.domain.entities import Chunk
from src.meridian.infrastructure.auth.firebase_auth import get_current_user
from src.meridian.infrastructure.database.models import Base, DBResearchJob, DBResearchReport
from src.meridian.interfaces.api.main import app
from src.meridian.interfaces.api.routers import research


def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-token"}


class FakeChunkRepository:
    last_call = None

    def __init__(self):
        self.calls = []

    async def search(self, job_id: str, query: str, top_k: int = 5) -> list[Chunk]:
        FakeChunkRepository.last_call = (job_id, query, top_k)
        self.calls.append((job_id, query, top_k))
        return [
            Chunk(
                document_id="doc-1",
                content="snippet",
                metadata={
                    "source": "arxiv",
                    "title": "Threat Actor Tradecraft",
                    "url": "https://example.com/paper",
                    "snippet": "Evidence snippet",
                },
                credibility_score=0.91,
            )
        ]


class ZeroCredibilityChunkRepository:
    async def search(self, job_id: str, query: str, top_k: int = 5) -> list[Chunk]:
        return [
            Chunk(
                document_id="doc-2",
                content="zero credibility snippet",
                metadata={
                    "source": "web",
                    "title": "Zero Credibility Source",
                    "url": "https://example.com/zero",
                    "snippet": "Zero credibility evidence",
                },
                credibility_score=0.0,
            )
        ]


@pytest_asyncio.fixture
async def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "research-router.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = async_sessionmaker(bind=engine, autoflush=False, autocommit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    async def override_get_current_user():
        return {"uid": "user-123", "email": "user@example.com"}

    monkeypatch.setattr(research, "ChromaChunkRepository", FakeChunkRepository, raising=False)
    FakeChunkRepository.last_call = None
    app.dependency_overrides[research.get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with session_factory() as session:
        completed_report = DBResearchReport(
            id="report-123",
            job_id="job-123",
            query="threat actor report",
            markdown_content="# Threat Actor Report",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            workspace_metadata=json.dumps(
                {
                    "domain": "computer_science",
                    "format_label": "osint",
                    "display_query": "threat actor report",
                    "execution_query": "threat actor report after:2022-01-01",
                    "current_phase": "synthesize",
                    "pipeline": {
                        "current_phase": "synthesize",
                        "phases": ["research", "chunk", "retrieve", "synthesize"],
                    },
                    "active_sources": ["arxiv", "ieee", "web"],
                    "query_refinements": [
                        {
                            "source": "arxiv",
                            "raw_query": "threat actor report after:2022-01-01",
                            "enriched_query": '"threat actor report after:2022-01-01" after:2022-01-01',
                        },
                        {
                            "source": "ieee",
                            "raw_query": "threat actor report after:2022-01-01",
                            "enriched_query": "threat actor report after:2022-01-01",
                        },
                    ],
                }
            ),
        )
        completed_job = DBResearchJob(
            id="job-123",
            user_id="user-123",
            query="threat actor report",
            status="completed",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            completed_at=datetime(2024, 1, 1, 0, 30, 0),
            error_message=None,
            workspace_metadata=json.dumps(
                {
                    "domain": "computer_science",
                    "format_label": "osint",
                    "display_query": "threat actor report",
                    "execution_query": "threat actor report after:2022-01-01",
                    "current_phase": "synthesize",
                    "pipeline": {
                        "current_phase": "synthesize",
                        "phases": ["research", "chunk", "retrieve", "synthesize"],
                    },
                    "active_sources": ["arxiv", "ieee", "web"],
                }
            ),
        )
        session.add(completed_job)
        session.add(completed_report)
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as async_client:
        yield async_client

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_get_research_report_returns_workspace_metadata(client):
    response = await client.get("/research/job-123/report", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "threat actor report"
    assert payload["domain"] == "computer_science"
    assert payload["format_label"] == "osint"
    assert payload["pipeline"]["current_phase"] == "synthesize"
    assert payload["evidence"][0]["source"] == "arxiv"
    assert FakeChunkRepository.last_call == ("job-123", "threat actor report after:2022-01-01", 10)
    assert payload["explainability"]["active_sources"] == ["arxiv", "ieee", "web"]
    assert payload["explainability"]["query_refinements"] == [
        {
            "source": "arxiv",
            "raw_query": "threat actor report after:2022-01-01",
            "enriched_query": '"threat actor report after:2022-01-01" after:2022-01-01',
        },
        {
            "source": "ieee",
            "raw_query": "threat actor report after:2022-01-01",
            "enriched_query": "threat actor report after:2022-01-01",
        },
    ]


@pytest.mark.asyncio
async def test_get_research_report_does_not_use_job_status_as_pipeline_phase(client):
    response = await client.get("/research/job-123/report", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["pipeline"]["current_phase"] == "synthesize"


@pytest.mark.asyncio
async def test_get_research_report_returns_null_phase_when_workspace_phase_is_unavailable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "research-router-missing-phase.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = async_sessionmaker(bind=engine, autoflush=False, autocommit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    async def override_get_current_user():
        return {"uid": "user-123", "email": "user@example.com"}

    monkeypatch.setattr(research, "ChromaChunkRepository", FakeChunkRepository, raising=False)
    app.dependency_overrides[research.get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with session_factory() as session:
        session.add(
        DBResearchJob(
            id="job-no-phase",
            user_id="user-123",
            query="threat actor report",
            status="completed",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            completed_at=datetime(2024, 1, 1, 0, 30, 0),
            error_message=None,
            workspace_metadata=json.dumps(
                {
                    "domain": "computer_science",
                    "format_label": "osint",
                    "display_query": "threat actor report",
                    "execution_query": "threat actor report after:2022-01-01",
                    "active_sources": ["arxiv"],
                }
            ),
            )
        )
        session.add(
        DBResearchReport(
            id="report-no-phase",
            job_id="job-no-phase",
            query="threat actor report",
            markdown_content="# Threat Actor Report",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            workspace_metadata=json.dumps(
                {
                    "domain": "computer_science",
                    "format_label": "osint",
                    "display_query": "threat actor report",
                    "execution_query": "threat actor report after:2022-01-01",
                    "active_sources": ["arxiv"],
                }
            ),
        )
        )
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as async_client:
        response = await async_client.get("/research/job-no-phase/report", headers=auth_headers())

    app.dependency_overrides.clear()
    await engine.dispose()

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "threat actor report"
    assert payload["pipeline"]["current_phase"] is None


@pytest.mark.asyncio
async def test_get_research_report_preserves_zero_credibility_scores(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(research, "ChromaChunkRepository", ZeroCredibilityChunkRepository, raising=False)

    response = await client.get("/research/job-123/report", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["evidence"][0]["credibility_score"] == 0.0


@pytest.mark.asyncio
async def test_get_research_status_rejects_non_owner(client):
    async def override_get_current_user():
        return {"uid": "user-456", "email": "other@example.com"}

    app.dependency_overrides[get_current_user] = override_get_current_user

    response = await client.get("/research/job-123", headers=auth_headers())

    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


@pytest.mark.asyncio
async def test_get_research_report_rejects_non_owner(client):
    async def override_get_current_user():
        return {"uid": "user-456", "email": "other@example.com"}

    app.dependency_overrides[get_current_user] = override_get_current_user

    response = await client.get("/research/job-123/report", headers=auth_headers())

    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


@pytest.mark.asyncio
async def test_create_research_commits_job_before_queue_dispatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "research-router-create.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = async_sessionmaker(bind=engine, autoflush=False, autocommit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    async def override_get_current_user():
        return {"uid": "user-123", "email": "user@example.com"}

    monkeypatch.setattr(research.run_research_pipeline, "delay", lambda _job_id: None)
    app.dependency_overrides[research.get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as async_client:
        response = await async_client.post(
            "/research/",
            headers=auth_headers(),
            json={
                "query": "fresh research",
                "execution_query": "fresh research after:2022-01-01",
                "advanced_options": {
                    "recentOnly": True,
                    "requireMultipleSources": False,
                    "reportDepth": "deep",
                },
            },
        )

    async with session_factory() as session:
        stored_job = await session.get(DBResearchJob, response.json()["id"])

    app.dependency_overrides.clear()
    await engine.dispose()

    assert response.status_code == 200
    assert stored_job is not None
    assert stored_job.query == "fresh research"
    metadata = json.loads(stored_job.workspace_metadata)
    assert metadata["display_query"] == "fresh research"
    assert metadata["execution_query"] == "fresh research after:2022-01-01"
    assert metadata["advanced_options"] == {
        "recentOnly": True,
        "requireMultipleSources": False,
        "reportDepth": "deep",
    }
    assert response.json()["query"] == "fresh research"
