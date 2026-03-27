import asyncio
from weakref import WeakSet

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, async_sessionmaker, create_async_engine

from src.meridian.infrastructure.database.models import Base

DATABASE_URL = "sqlite+aiosqlite:///meridian.db"
engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(bind=engine, autoflush=False, autocommit=False)
_database_bootstrap_lock = asyncio.Lock()
_bootstrapped_targets: WeakSet[AsyncEngine] = WeakSet()


async def _ensure_column(
    conn: AsyncConnection,
    table_name: str,
    column_name: str,
    column_type: str = "TEXT",
) -> None:
    result = await conn.execute(text(f"PRAGMA table_info({table_name})"))
    existing_columns = {row[1] for row in result.all()}
    if column_name in existing_columns:
        return

    try:
        await conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))
    except OperationalError:
        retry_result = await conn.execute(text(f"PRAGMA table_info({table_name})"))
        retry_columns = {row[1] for row in retry_result.all()}
        if column_name not in retry_columns:
            raise


async def _ensure_workspace_metadata_columns(conn: AsyncConnection) -> None:
    table_columns = {
        "research_jobs": ("workspace_metadata", "TEXT"),
        "research_reports": ("workspace_metadata", "TEXT"),
    }

    for table_name, (column_name, column_type) in table_columns.items():
        await _ensure_column(conn, table_name, column_name, column_type)


async def init_db(database_engine: AsyncEngine | None = None) -> None:
    target_engine = database_engine or engine

    if target_engine in _bootstrapped_targets:
        return

    async with _database_bootstrap_lock:
        if target_engine in _bootstrapped_targets:
            return

        async with target_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await _ensure_workspace_metadata_columns(conn)

        _bootstrapped_targets.add(target_engine)
