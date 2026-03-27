# Meridian Production Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Meridian production-ready by closing credential/runtime gaps, exposing real workspace metadata through the API, wiring the UI to truthful payloads, adding release-grade tests, and documenting deployment/operations.

**Architecture:** Keep the current integrated branch as the release candidate and harden it in layered order: runtime configuration first, API contract second, frontend wiring third, quality gates fourth, and deployment documentation last. Avoid changing the domain model unnecessarily; prefer API DTO expansion and frontend data normalization over deep backend entity reshaping.

**Tech Stack:** FastAPI, SQLAlchemy, Celery, Firebase Admin, React 19, Vite, Tailwind, Vitest + Testing Library, Playwright, pytest

---

## File Map

### Backend runtime and auth

- Modify: `src/meridian/infrastructure/auth/firebase_auth.py`
- Modify: `.env.example`
- Create: `docs/production/credentials.md`
- Create: `docs/production/runbook.md`
- Test: `tests/infrastructure/auth/test_firebase_auth.py`

### Backend API contract and workspace payload

- Modify: `src/meridian/interfaces/api/routers/research.py`
- Modify: `src/meridian/application/pipeline/orchestrator.py`
- Modify: `src/meridian/interfaces/workers/tasks.py`
- Create: `src/meridian/interfaces/api/schemas/research_workspace.py`
- Test: `tests/interfaces/api/test_research_router.py`
- Modify: `tests/application/pipeline/test_orchestrator.py`

### Frontend API and workspace rendering

- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/pages/ResearchWorkspacePage.tsx`
- Modify: `frontend/src/components/detail/ExplainabilityPanel.tsx`
- Replace: `frontend/src/components/detail/EvidencePlaceholder.tsx`
- Modify: `frontend/src/components/detail/PipelineTimeline.tsx`
- Modify: `frontend/src/components/detail/ReportHeader.tsx`
- Modify: `frontend/src/pages/LoginPage.tsx`

### Frontend test harness

- Modify: `frontend/package.json`
- Modify: `frontend/vite.config.ts`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/src/test/render-with-providers.tsx`
- Create: `frontend/src/pages/__tests__/LoginPage.test.tsx`
- Create: `frontend/src/pages/__tests__/ResearchWorkspacePage.test.tsx`
- Create: `frontend/src/pages/__tests__/ResearchDashboardPage.test.tsx`

### Browser E2E and deployment readiness

- Create: `frontend/playwright.config.ts`
- Create: `frontend/e2e/login-setup.spec.ts`
- Create: `frontend/e2e/workspace-happy-path.spec.ts`
- Create: `docs/production/deployment-checklist.md`

---

### Task 1: Harden Runtime Configuration And Firebase Admin Startup

**Files:**
- Modify: `src/meridian/infrastructure/auth/firebase_auth.py`
- Modify: `.env.example`
- Modify: `frontend/.env.example`
- Test: `tests/infrastructure/auth/test_firebase_auth.py`
- Create: `docs/production/credentials.md`

- [ ] **Step 1: Write the failing backend auth/runtime tests**

```python
from fastapi import HTTPException

from src.meridian.infrastructure.auth import firebase_auth


def test_get_current_user_returns_503_when_auth_sdk_missing(monkeypatch):
    monkeypatch.setattr(firebase_auth, "auth", None)

    class DummyCreds:
        credentials = "token"

    try:
        import anyio

        anyio.run(firebase_auth.get_current_user, DummyCreds())
    except HTTPException as exc:
        assert exc.status_code == 503
        assert "Firebase auth is not available" in exc.detail
    else:
        raise AssertionError("Expected HTTPException")


def test_firebase_setup_state_marks_missing_admin_credentials(monkeypatch):
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    setup = firebase_auth.describe_firebase_setup()
    assert setup["admin_credentials_available"] is False
    assert "GOOGLE_APPLICATION_CREDENTIALS" in setup["message"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests\infrastructure\auth\test_firebase_auth.py -q`
Expected: FAIL because `describe_firebase_setup()` does not exist yet and runtime setup state is not exposed.

- [ ] **Step 3: Implement explicit Firebase Admin setup reporting and env examples**

```python
def describe_firebase_setup() -> dict[str, object]:
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    has_service_account = bool(cred_path and os.path.exists(cred_path))
    return {
        "auth_sdk_available": auth is not None,
        "admin_credentials_available": has_service_account,
        "message": (
            "Firebase Admin is configured."
            if has_service_account
            else "Firebase Admin requires GOOGLE_APPLICATION_CREDENTIALS or valid ADC."
        ),
    }
```

```dotenv
OPENROUTER_API_KEY=your_openrouter_api_key_here
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/firebase-service-account.json
IEEE_API_KEY=your_ieee_api_key_here
SIMILARITY_WEIGHT=0.7
CREDIBILITY_WEIGHT=0.3
WEB_CREDIBILITY_AUDIT_LIMIT=5
```

```markdown
# Meridian Credentials

## Required

- `OPENROUTER_API_KEY`
- `GOOGLE_APPLICATION_CREDENTIALS`
- frontend Firebase web config in `frontend/.env`

## Optional

- `IEEE_API_KEY`
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests\infrastructure\auth\test_firebase_auth.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .env.example frontend/.env.example src/meridian/infrastructure/auth/firebase_auth.py tests/infrastructure/auth/test_firebase_auth.py docs/production/credentials.md
git commit -m "chore: document and validate meridian runtime credentials"
```

### Task 2: Expose A Truthful Workspace API Contract

**Files:**
- Create: `src/meridian/interfaces/api/schemas/research_workspace.py`
- Modify: `src/meridian/interfaces/api/routers/research.py`
- Modify: `src/meridian/application/pipeline/orchestrator.py`
- Modify: `tests/interfaces/api/test_research_router.py`
- Modify: `tests/application/pipeline/test_orchestrator.py`

- [ ] **Step 1: Write failing API and orchestrator tests for workspace metadata**

```python
def test_get_research_report_returns_workspace_metadata(client, completed_report):
    response = client.get(f"/api/research/{completed_report.job_id}/report", headers=auth_headers())
    payload = response.json()
    assert payload["domain"] == "computer_science"
    assert payload["format_label"] == "osint"
    assert payload["pipeline"]["current_phase"] == "synthesize"
    assert payload["evidence"][0]["source"] == "arxiv"
    assert payload["explainability"]["query_refinements"][0]["enriched_query"]


def test_run_pipeline_logs_and_persists_workspace_metadata(orchestrator, caplog):
    report = anyio.run(orchestrator.run_pipeline, "job-123", "threat actor report")
    assert report.metadata["domain"] == "computer_science"
    assert report.metadata["format_label"] == "osint"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests\interfaces\api\test_research_router.py tests\application\pipeline\test_orchestrator.py -q`
Expected: FAIL because the router only returns report markdown and the orchestrator does not surface a workspace payload.

- [ ] **Step 3: Add explicit workspace/report schemas and route payload assembly**

```python
class EvidenceItem(BaseModel):
    source: str
    title: str
    url: str | None = None
    credibility_score: float = 0.5
    snippet: str | None = None


class ExplainabilityPayload(BaseModel):
    active_sources: list[str]
    query_refinements: list[dict[str, str]]


class ResearchWorkspaceResponse(BaseModel):
    id: str
    job_id: str
    query: str
    markdown_content: str
    domain: str | None = None
    format_label: str | None = None
    pipeline: dict[str, str | list[str]]
    evidence: list[EvidenceItem]
    explainability: ExplainabilityPayload
```

```python
return ResearchWorkspaceResponse(
    id=report.id,
    job_id=report.job_id,
    query=report.query,
    markdown_content=report.markdown_content,
    domain=job.metadata.get("domain"),
    format_label=job.metadata.get("format_label"),
    pipeline={"current_phase": job.metadata.get("current_phase", job.status), "phases": PHASES},
    evidence=build_evidence_items(job.metadata),
    explainability=build_explainability_payload(job.metadata),
)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests\interfaces\api\test_research_router.py tests\application\pipeline\test_orchestrator.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/meridian/interfaces/api/schemas/research_workspace.py src/meridian/interfaces/api/routers/research.py src/meridian/application/pipeline/orchestrator.py tests/interfaces/api/test_research_router.py tests/application/pipeline/test_orchestrator.py
git commit -m "feat: expose meridian workspace metadata through the api"
```

### Task 3: Replace Workspace Placeholders With Real Data

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/pages/ResearchWorkspacePage.tsx`
- Modify: `frontend/src/components/detail/ExplainabilityPanel.tsx`
- Modify: `frontend/src/components/detail/PipelineTimeline.tsx`
- Modify: `frontend/src/components/detail/ReportHeader.tsx`
- Replace: `frontend/src/components/detail/EvidencePlaceholder.tsx`

- [ ] **Step 1: Write failing frontend workspace tests against real payload fields**

```tsx
it('renders workspace explainability from the API payload', async () => {
  mockFetchWorkspace({
    domain: 'computer_science',
    format_label: 'osint',
    evidence: [{ source: 'arxiv', title: 'Threat clustering paper', credibility_score: 0.82 }],
    explainability: {
      active_sources: ['arxiv', 'web'],
      query_refinements: [{ source: 'web', raw_query: 'apt29 report', enriched_query: '"apt29 report" -site:reddit.com' }],
    },
    pipeline: { current_phase: 'synthesize', phases: ['classify', 'collect', 'score', 'chunk', 'retrieve', 'synthesize'] },
  })

  render(<ResearchWorkspacePage />)

  expect(await screen.findByText('computer_science')).toBeInTheDocument()
  expect(screen.getByText('Threat clustering paper')).toBeInTheDocument()
  expect(screen.getByText(/-site:reddit.com/)).toBeInTheDocument()
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test -- ResearchWorkspacePage`
Expected: FAIL because the frontend report type and components do not understand workspace metadata yet.

- [ ] **Step 3: Implement the frontend workspace data model and renderers**

```ts
export interface ResearchWorkspacePayload {
  id: string
  job_id: string
  query: string
  markdown_content: string
  domain?: string
  format_label?: string
  pipeline: { current_phase: string; phases: string[] }
  evidence: Array<{ source: string; title: string; credibility_score: number; snippet?: string; url?: string }>
  explainability: {
    active_sources: string[]
    query_refinements: Array<{ source: string; raw_query: string; enriched_query: string }>
  }
}
```

```tsx
<ReportHeader
  jobId={jobId}
  query={query}
  status={status}
  domain={workspace?.domain}
  formatLabel={workspace?.format_label}
/>

<PipelineTimeline status={status} phases={workspace?.pipeline?.phases} currentPhase={workspace?.pipeline?.current_phase} />

<EvidencePanel evidence={workspace?.evidence ?? []} />

<ExplainabilityPanel
  status={status}
  activeSources={workspace?.explainability.active_sources ?? []}
  queryRefinements={workspace?.explainability.query_refinements ?? []}
/>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm run test -- ResearchWorkspacePage`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/pages/ResearchWorkspacePage.tsx frontend/src/components/detail/ExplainabilityPanel.tsx frontend/src/components/detail/PipelineTimeline.tsx frontend/src/components/detail/ReportHeader.tsx frontend/src/components/detail/EvidencePlaceholder.tsx
git commit -m "feat: render real meridian workspace explainability"
```

### Task 4: Add Frontend Test Harness And Component Coverage

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/vite.config.ts`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/src/test/render-with-providers.tsx`
- Create: `frontend/src/pages/__tests__/LoginPage.test.tsx`
- Create: `frontend/src/pages/__tests__/ResearchDashboardPage.test.tsx`
- Create: `frontend/src/pages/__tests__/ResearchWorkspacePage.test.tsx`

- [ ] **Step 1: Write the failing test harness and first component tests**

```tsx
import { render, screen } from '@testing-library/react'
import LoginPage from '../LoginPage'

it('shows setup guidance when firebase is not configured', () => {
  render(<LoginPage />)
  expect(screen.getByText(/Finish workspace setup/i)).toBeInTheDocument()
})
```

```json
{
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest"
  }
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm run test`
Expected: FAIL because Vitest and Testing Library are not configured yet.

- [ ] **Step 3: Install and configure Vitest + Testing Library minimally**

```json
{
  "devDependencies": {
    "@testing-library/jest-dom": "^6.6.3",
    "@testing-library/react": "^16.3.0",
    "@testing-library/user-event": "^14.6.1",
    "jsdom": "^26.1.0",
    "vitest": "^3.2.4"
  }
}
```

```ts
/// frontend/vite.config.ts
test: {
  environment: 'jsdom',
  setupFiles: './src/test/setup.ts',
  globals: true,
}
```

```ts
// frontend/src/test/setup.ts
import '@testing-library/jest-dom'
```

```tsx
// frontend/src/test/render-with-providers.tsx
export function renderWithProviders(ui: React.ReactElement) {
  return render(<BrowserRouter>{ui}</BrowserRouter>)
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm run test`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.ts frontend/src/test/setup.ts frontend/src/test/render-with-providers.tsx frontend/src/pages/__tests__/LoginPage.test.tsx frontend/src/pages/__tests__/ResearchDashboardPage.test.tsx frontend/src/pages/__tests__/ResearchWorkspacePage.test.tsx
git commit -m "test: add meridian frontend component coverage"
```

### Task 5: Add Browser E2E Checks And Production Runbook

**Files:**
- Create: `frontend/playwright.config.ts`
- Create: `frontend/e2e/login-setup.spec.ts`
- Create: `frontend/e2e/workspace-happy-path.spec.ts`
- Create: `docs/production/runbook.md`
- Create: `docs/production/deployment-checklist.md`

- [ ] **Step 1: Write the failing E2E specs and runbook skeleton**

```ts
import { test, expect } from '@playwright/test'

test('setup state is visible when firebase env is absent', async ({ page }) => {
  await page.goto('/login')
  await expect(page.getByText('Finish workspace setup')).toBeVisible()
})
```

```ts
test('completed workspace shows report and evidence', async ({ page }) => {
  await page.goto('/workspace/demo-job')
  await expect(page.getByRole('heading', { name: /Meridian/i })).toBeVisible()
  await expect(page.getByText(/Evidence Surface|Threat clustering paper/)).toBeVisible()
})
```

```markdown
# Meridian Production Runbook

## Required services

- frontend hosting
- backend API
- Celery worker
- SQLite/Postgres storage target

## Required env

- backend: `OPENROUTER_API_KEY`, `GOOGLE_APPLICATION_CREDENTIALS`
- frontend: Firebase web config
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx playwright test`
Expected: FAIL because Playwright is not configured yet and specs are not wired into the frontend workflow.

- [ ] **Step 3: Add Playwright config and deployment documentation**

```json
{
  "devDependencies": {
    "@playwright/test": "^1.54.2"
  }
}
```

```ts
import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  use: {
    baseURL: 'http://127.0.0.1:4173',
    headless: true,
  },
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1 --port 4173',
    port: 4173,
    reuseExistingServer: true,
  },
})
```

```markdown
## Deployment Checklist

- configure backend secrets
- configure frontend Firebase env
- verify worker startup
- verify `/api/research` authenticated requests
- verify report generation end-to-end
- verify logs and health checks
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx playwright test`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/playwright.config.ts frontend/e2e/login-setup.spec.ts frontend/e2e/workspace-happy-path.spec.ts docs/production/runbook.md docs/production/deployment-checklist.md
git commit -m "docs: add meridian production runbook and e2e checks"
```

### Task 6: Run Final Integrated Verification

**Files:**
- Modify: none
- Test: existing backend and frontend verification commands

- [ ] **Step 1: Run backend regression suite**

```bash
pytest tests\test_domain.py tests\application\pipeline\test_domain_classifier.py tests\application\pipeline\test_source_router.py tests\application\pipeline\test_credibility_scorer.py tests\application\pipeline\test_chunking_service.py tests\application\pipeline\test_format_selector.py tests\application\pipeline\test_query_processor.py tests\application\pipeline\test_orchestrator.py tests\infrastructure\external_apis\test_existing_source_clients.py tests\infrastructure\external_apis\test_new_source_clients.py tests\infrastructure\llm\test_research_agent.py tests\infrastructure\llm\test_synthesizer.py tests\infrastructure\vector_store\test_chroma_repository.py tests\interfaces\workers\test_tasks.py tests\interfaces\api\test_research_router.py tests\infrastructure\auth\test_firebase_auth.py -q
```

- [ ] **Step 2: Run frontend verification**

```bash
npm run lint
npm run build
npm run test
npx playwright test
```

- [ ] **Step 3: Capture remaining warnings honestly**

```markdown
- Pydantic `copy()` deprecation warnings may still appear until separately refactored.
- IEEE remains optional and should be called out as such in production docs.
- Any unresolved `npm audit` issues should be listed explicitly before launch.
```

- [ ] **Step 4: Confirm clean branch state**

Run: `git status --short --branch`
Expected: `## codex/phase-a-domain-routing`

- [ ] **Step 5: Commit final verification documentation updates**

```bash
git add docs/production/runbook.md docs/production/deployment-checklist.md
git commit -m "chore: finalize meridian production readiness verification"
```
