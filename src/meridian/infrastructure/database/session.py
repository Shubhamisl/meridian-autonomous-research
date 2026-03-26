from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from src.meridian.infrastructure.database.models import Base

DATABASE_URL = "sqlite+aiosqlite:///meridian.db"
engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(bind=engine, autoflush=False, autocommit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
