# Meridian

**Autonomous Research Intelligence Engine**

Meridian accepts a natural-language research query, spins up an async pipeline
that ingests from arXiv, NewsAPI, and Wikipedia, builds a vector knowledge base,
runs an LLM agent loop to iteratively gather evidence, then synthesises a
structured report with citations — all without human-in-the-loop.

---

## Architecture

```
POST /research  ─►  FastAPI  ─►  Background Task (or Celery)
                                         │
                          ┌──────────────▼──────────────┐
                          │      PipelineOrchestrator    │
                          │                              │
                          │  1. ResearchAgent (Claude)   │
                          │     ├─ search_arxiv          │
                          │     ├─ search_news           │
                          │     ├─ search_wikipedia      │
                          │     └─ query_knowledge_base  │
                          │                              │
                          │  2. Chunk + embed docs       │
                          │     └─ chromadb              │
                          │                              │
                          │  3. RAG retrieval            │
                          │                              │
                          │  4. ReportSynthesizer        │
                          └──────────────────────────────┘
                                         │
                              ResearchReport (PostgreSQL)
```

### Design principles

- **Clean / Hexagonal architecture**: domain entities live in `domain/` with
  zero infrastructure imports. Infrastructure adapters implement abstract
  repository interfaces. FastAPI is one of many possible delivery mechanisms.

- **Immutable domain objects**: all entities are frozen Pydantic models.
  State transitions return new instances (`job.start()`, `job.fail(...)`).

- **Async-first**: everything from HTTP clients to DB queries uses `async/await`.
  Document embedding is fan-out with bounded concurrency via `asyncio.Semaphore`.

- **Agentic loop**: `ResearchAgent` runs until Claude calls `finish_research`,
  not for a fixed number of steps. The agent decides when it has enough evidence.

---

## Tech stack

| Concern | Library |
|---|---|
| API framework | FastAPI + Pydantic v2 |
| LLM | Anthropic Claude (tool-use API) |
| Vector store | ChromaDB |
| Relational DB | PostgreSQL via SQLAlchemy 2.0 (async) |
| Task queue | Celery + Redis |
| HTTP client | httpx (async) |
| Containerisation | Docker + docker-compose |
| Testing | pytest-asyncio, pytest-httpx |

---

## Quick start

```bash
# 1. Clone and set up environment
git clone https://github.com/yourname/meridian.git
cd meridian
cp .env.example .env
# Edit .env — add ANTHROPIC_API_KEY and NEWS_API_KEY

# 2. Start all services
docker compose up --build

# 3. Submit a research query
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"query": "Recent advances in retrieval-augmented generation"}'
# → {"id": "abc-123", "status": "pending", ...}

# 4. Poll until completed
curl http://localhost:8000/research/abc-123

# 5. Retrieve the report
curl http://localhost:8000/research/abc-123/report
```

Celery monitoring UI is available at http://localhost:5555.

---

## Project structure

```
src/meridian/
├── domain/
│   ├── entities.py          # ResearchJob, Document, Chunk, ResearchReport
│   └── repositories.py      # Abstract repository interfaces (ports)
│
├── application/
│   ├── pipeline/
│   │   └── orchestrator.py  # 4-phase pipeline coordinator
│   └── use_cases/
│       └── create_research.py
│
├── infrastructure/
│   ├── llm/
│   │   ├── research_agent.py   # Claude tool-calling loop
│   │   └── synthesizer.py      # Report synthesis LLM call
│   ├── external_apis/
│   │   ├── arxiv_client.py
│   │   ├── news_client.py
│   │   └── wikipedia_client.py
│   ├── vector_store/
│   │   └── chroma_repository.py
│   └── database/
│       ├── models.py            # SQLAlchemy ORM models
│       └── postgres_repositories.py
│
└── interfaces/
    ├── api/
    │   ├── main.py              # FastAPI app factory
    │   ├── dependencies.py      # DI wiring
    │   └── routers/
    │       └── research.py
    └── workers/
        ├── app.py               # Celery app
        └── tasks.py             # research_pipeline task
```

---

## Running tests

```bash
pip install -e ".[dev]"
pytest tests/ -v --asyncio-mode=auto
```

Key test patterns used:
- Repository fakes (in-memory implementations) for fast unit tests
- `pytest-httpx` to mock external API calls
- Frozen-time fixtures for deterministic `created_at` fields
- Integration tests spin up real containers via `pytest-docker`

---

## Extending Meridian

| What | Where |
|---|---|
| Add a new data source | Implement the `ExternalAPIClient` protocol in `infrastructure/external_apis/` and add a new tool schema to `TOOLS` in `research_agent.py` |
| Swap vector DB | Implement `ChunkRepository` ABC in `infrastructure/vector_store/` |
| Add streaming report output | Add a `GET /research/{id}/stream` endpoint using FastAPI's `StreamingResponse` |
| Add auth | Add an OAuth2 dependency to `interfaces/api/dependencies.py` |
