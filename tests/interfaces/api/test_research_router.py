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
    async def search(self, job_id: str, query: str, top_k: int = 5) -> list[Chunk]:
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
                    "current_phase": "synthesize",
                    "pipeline": {
                        "current_phase": "synthesize",
                        "phases": ["research", "chunk", "retrieve", "synthesize"],
                    },
                    "active_sources": ["arxiv", "ieee", "web"],
                    "query_refinements": [
                        {
                            "source": "arxiv",
                            "raw_query": "threat actor report",
                            "enriched_query": "\"threat actor report\" after:2022-01-01",
                        }
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
                    "current_phase": "synthesize",
                    "pipeline": {
                        "current_phase": "synthesize",
                        "phases": ["research", "chunk", "retrieve", "synthesize"],
                    },
                    "active_sources": ["arxiv", "ieee", "web"],
                    "query_refinements": [
                        {
                            "source": "arxiv",
                            "raw_query": "threat actor report",
                            "enriched_query": "\"threat actor report\" after:2022-01-01",
                        }
                    ],
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
    assert payload["domain"] == "computer_science"
    assert payload["format_label"] == "osint"
    assert payload["pipeline"]["current_phase"] == "synthesize"
    assert payload["evidence"][0]["source"] == "arxiv"
    assert payload["explainability"]["query_refinements"][0]["enriched_query"]
