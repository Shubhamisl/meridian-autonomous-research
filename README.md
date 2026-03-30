# Meridian

Meridian is an autonomous research intelligence engine that turns a natural-language question into a structured report with source gathering, credibility-aware retrieval, and a guided workspace UI.

It is built as a local-first full-stack application:

- `FastAPI` API for job creation and report retrieval
- `Celery` worker for background research execution
- `React + Vite` frontend workspace
- `SQLite` for local job/report persistence
- `ChromaDB` for vector retrieval
- `OpenRouter` for classification, agentic research, credibility checks, and synthesis
- `Firebase` for frontend sign-in and backend token verification

## What Meridian Does Today

Meridian currently supports:

- domain classification before research begins
- source routing by domain
- multi-tool research with query enrichment
- credibility scoring and weighted retrieval
- format-aware synthesis
- a dashboard plus workspace-style frontend
- explainability metadata such as sources, refinements, and pipeline phase

Current research domains:

- `biomedical`
- `computer_science`
- `economics`
- `legal`
- `general`

Current source adapters:

- Wikipedia
- web search
- arXiv
- PubMed
- IEEE Xplore
- Semantic Scholar

## Architecture At A Glance

Meridian follows a Clean/Hexagonal structure:

```text
frontend (React/Vite)
    |
    v
FastAPI API
    |
    v
Celery task -> PipelineOrchestrator
    |
    +--> ResearchAgent
    |      +--> DomainClassifier
    |      +--> SourceRouter
    |      +--> QueryProcessor
    |      +--> External source adapters
    |
    +--> ChunkingService
    |      +--> CredibilityScorer
    |
    +--> ChromaChunkRepository
    |
    +--> FormatSelector
    |
    +--> ReportSynthesizer
```

Code layout:

```text
src/meridian/
|- domain/                  # entities + repository protocols
|- application/pipeline/    # orchestration and application services
|- infrastructure/          # adapters: LLM, DB, vector store, external APIs
`- interfaces/              # FastAPI + Celery wiring

frontend/
|- src/components/
|- src/pages/
`- src/lib/
```

## Current Stack

| Concern | Current implementation |
|---|---|
| API | FastAPI |
| Worker | Celery |
| Frontend | React 19 + Vite |
| LLM provider | OpenRouter |
| Local relational persistence | SQLite |
| Vector store | ChromaDB |
| Auth | Firebase |
| Background broker/backend | SQLite-backed Celery by default |

Important notes:

- The repository contains `Dockerfile` and `docker-compose.yml`, but the current recommended way to run Meridian is the local dev flow below.
- The README reflects the app as it runs today, not an aspirational deployment target.

## Local Development

### 1. Prerequisites

- Python 3.10+ or 3.11
- Node.js 20+
- npm
- a Firebase project for frontend auth
- an OpenRouter API key

Optional:

- IEEE API key for IEEE Xplore results

### 2. Backend environment

Copy `.env.example` to `.env` and fill in the values:

```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/firebase-service-account.json
IEEE_API_KEY=your_ieee_api_key_here
SIMILARITY_WEIGHT=0.7
CREDIBILITY_WEIGHT=0.3
WEB_CREDIBILITY_AUDIT_LIMIT=5
```

Notes:

- `GOOGLE_APPLICATION_CREDENTIALS` should point to a Firebase Admin service-account JSON on your machine.
- `IEEE_API_KEY` is optional. If omitted, IEEE search is skipped gracefully.

### 3. Frontend environment

Copy `frontend/.env.example` to `frontend/.env` and fill in your Firebase web config:

```env
VITE_FIREBASE_API_KEY=your_firebase_api_key
VITE_FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your_project_id
VITE_FIREBASE_STORAGE_BUCKET=your_project.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=your_sender_id
VITE_FIREBASE_APP_ID=your_app_id
```

### 4. Install dependencies

Backend:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Frontend:

```bash
cd frontend
npm install
cd ..
```

### 5. Run Meridian

On Windows, the simplest option is:

```bat
run.bat
```

That starts:

- Celery worker
- FastAPI API on `http://127.0.0.1:8000`
- Vite frontend on `http://localhost:5173`

Manual startup is also fine.

Backend API:

```bash
venv\Scripts\activate
set PYTHONPATH=%cd%
uvicorn src.meridian.interfaces.api.main:app --reload --port 8000
```

Worker:

```bash
venv\Scripts\activate
set PYTHONPATH=%cd%
celery -A src.meridian.interfaces.workers.app worker --loglevel=info -P solo
```

Frontend:

```bash
cd frontend
npm run dev
```

## Using The App

1. Open the frontend in your browser.
2. Sign in with Firebase-backed Google auth.
3. Create a research job from the dashboard.
4. Follow the job in the workspace until the report completes.

Core API endpoints:

- `GET /health`
- `POST /research/`
- `GET /research/`
- `GET /research/{job_id}`
- `GET /research/{job_id}/report`

## How Research Runs

Each job goes through these phases:

1. `research`
   - classify the query
   - select tools by domain
   - enrich search queries
   - gather evidence through the research agent
2. `chunk`
   - split documents into chunks
   - score credibility
3. `retrieve`
   - run Chroma similarity search
   - re-rank using credibility-aware weighting
4. `synthesize`
   - select report format
   - generate the final report

The frontend workspace surfaces:

- report status
- pipeline phase
- domain and format
- evidence cards
- active sources
- query refinements

## Testing

Backend:

```bash
set PYTHONPATH=%cd%
python -m pytest tests -q
```

Frontend:

```bash
cd frontend
npm test
npm run lint
npm run build
```

There are also Playwright-based browser tests in the frontend project.

## Local Data And Runtime Artifacts

Meridian creates local runtime state in the repo root by default:

- `meridian.db`
- `celery_broker.db`
- `celery_results.db`
- `chroma_db/`

These are ignored by git and should not be committed.

## Known Constraints

- The current default deployment posture is local-first, not production-hardened cloud hosting.
- Free OpenRouter models may rate-limit or change availability.
- Some legal or thin-source queries may still depend heavily on web and Wikipedia coverage.
- The repo still has a few non-blocking Pydantic deprecation warnings around `copy()`.
- Frontend build currently warns about a large JS bundle.

## Security Notes

- Never commit `.env`, `frontend/.env`, Firebase Admin JSON files, or local database files.
- Keep `GOOGLE_APPLICATION_CREDENTIALS` pointing to a local file path outside version control.
- Review git status before pushing if you generate local debug artifacts or screenshots.

## Repository Status

This repository reflects the current working Meridian stack, including:

- multi-phase research pipeline upgrades
- redesigned frontend workspace
- structured advanced research options
- truth-preserving display query vs execution query handling

If you are evaluating the project on GitHub, the best way to assess it is:

1. read this README
2. review the pipeline modules under `src/meridian/application/pipeline`
3. run the frontend and backend locally
4. submit a research query through the UI
