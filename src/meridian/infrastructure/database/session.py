from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, async_sessionmaker, create_async_engine

from src.meridian.infrastructure.database.models import Base

DATABASE_URL = "sqlite+aiosqlite:///meridian.db"
engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(bind=engine, autoflush=False, autocommit=False)


async def _ensure_workspace_metadata_columns(conn: AsyncConnection) -> None:
    table_columns = {
        "research_jobs": "workspace_metadata",
        "research_reports": "workspace_metadata",
    }

    for table_name, column_name in table_columns.items():
        result = await conn.execute(text(f"PRAGMA table_info({table_name})"))
        existing_columns = {row[1] for row in result.all()}
        if column_name not in existing_columns:
            await conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} TEXT"))


async def init_db(database_engine: AsyncEngine | None = None) -> None:
    target_engine = database_engine or engine
    async with target_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _ensure_workspace_metadata_columns(conn)
