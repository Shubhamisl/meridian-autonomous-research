from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.meridian.interfaces.api.routers import research
from src.meridian.infrastructure.database.session import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup step at the start of app
    await init_db()
    yield
    # Teardown step
    pass

app = FastAPI(title="Meridian API", lifespan=lifespan)
app.include_router(research.router, prefix="/research", tags=["research"])

@app.get("/health")
async def health_check():
    return {"status": "ok"}
