# Meridian Production Readiness Design

Date: 2026-03-27
Branch: `codex/phase-a-domain-routing`

## Goal

Take Meridian from "backend phases implemented and UI redesigned" to a production-ready system that is deployable, observable, and honest end-to-end. Production readiness here means:

- required credentials and runtime configuration are documented and validated
- the frontend surfaces real Meridian intelligence instead of placeholders
- the integrated user journey is covered by meaningful automated checks
- deployment and operational basics exist so the system can be run and debugged confidently

This is not a new product redesign. It is the final hardening and completion pass on the current integrated branch.

## Current State

### What is already complete

- Backend Phases A-D are implemented:
  - domain classification and source routing
  - credibility scoring and weighted retrieval
  - format-aware synthesis
  - query enrichment
- The new Meridian frontend is implemented:
  - dashboard
  - workspace
  - setup-aware login shell
- The integrated branch currently passes:
  - backend regression suite
  - frontend lint
  - frontend build

### What still feels incomplete

- The workspace still uses placeholders for evidence and explainability.
- The API does not yet expose the backend metadata the UI needs to fully reflect Meridian's behavior.
- Production credentials are only partially identified/configured.
- The integrated product lacks full end-to-end quality gates.
- Deployment and ops guidance are not yet production-grade.

## Non-Goals

- Do not redesign the domain layer beyond what is already approved.
- Do not add unrelated product features outside production-readiness needs.
- Do not block release on IEEE integration; IEEE remains optional until credentials are available.

## Track A: Secrets And Runtime Readiness

### Objective

Ensure Meridian can boot and authenticate correctly in production environments, with all required secrets identified and documented.

### Required backend credentials

- `OPENROUTER_API_KEY`
- Firebase Admin credentials for backend auth verification

### Optional backend credentials

- `IEEE_API_KEY`

If `IEEE_API_KEY` is absent, Meridian should continue operating and log a warning when IEEE-backed search is requested.

### Required frontend credentials

- `VITE_FIREBASE_API_KEY`
- `VITE_FIREBASE_AUTH_DOMAIN`
- `VITE_FIREBASE_PROJECT_ID`
- `VITE_FIREBASE_STORAGE_BUCKET`
- `VITE_FIREBASE_MESSAGING_SENDER_ID`
- `VITE_FIREBASE_APP_ID`

### Design decisions

- The frontend keeps its current graceful setup-aware fallback when Firebase config is missing.
- The backend must explicitly document and validate Firebase Admin requirements rather than assuming local developer state.
- Environment configuration should distinguish:
  - required
  - optional
  - dev-only

### Deliverables

- updated backend `.env.example`
- updated frontend `.env.example` if needed
- production env documentation
- startup validation notes in the runbook

## Track B: Product Completeness Through API Contract Expansion

### Objective

Expose the backend intelligence already computed by Meridian so the frontend can render a truthful, inspectable workspace.

### Current UI gaps

The following UI surfaces are intentionally placeholders because the API does not yet return the necessary data:

- evidence surface
- explainability panel
- domain/format metadata pills
- pipeline progress detail

### Required API additions

Research job status/report responses should be expanded to expose enough data for the frontend to render:

- detected domain
- selected format label
- active source set
- pipeline phase or phase events
- evidence/source entries
- credibility scores
- query refinement or enriched query audit trail

### Recommended response shape

The API should avoid forcing the frontend to reconstruct Meridian internals from scattered endpoints. Prefer either:

- one enriched workspace payload for the detail view

or

- a compact status payload plus a richer report payload with explicit explainability sections

The recommended choice is a richer report/workspace payload because the frontend detail page is already centered around one workspace view.

### Design decisions

- The frontend should only display real metadata returned by the API, not inferred placeholders once the contract is available.
- Explainability should remain progressive-disclosure UI, not dominate the reading surface.
- Evidence payloads should be normalized for cards and citations, not dump raw internal models directly.

### Deliverables

- backend API contract update
- frontend API client updates
- replacement of placeholder components with real data-driven components

## Track C: Quality Gates

### Objective

Establish enough automated confidence to support a production release of the integrated Meridian product.

### Required checks

- backend regression suite remains green
- frontend lint and build remain green
- frontend component/integration tests for:
  - login/setup fallback
  - dashboard rendering
  - workspace loading states
  - workspace completed state
- API contract tests for any new workspace/report payload fields
- one browser E2E happy path:
  - authenticate
  - create a research job
  - observe progress
  - open completed workspace
  - verify report and evidence render
- one browser E2E failure path:
  - failed job or missing setup state renders gracefully

### Design decisions

- This is not a mandate for exhaustive test coverage. The purpose is to prove the integrated product works end-to-end.
- Existing backend warnings that do not indicate regressions can remain tracked separately, but must be called out.

## Track D: Deployment And Operations

### Objective

Make Meridian deployable and supportable in production.

### Required operational capabilities

- frontend deployment target
- backend deployment target
- production environment variable mapping
- CORS/proxy/domain configuration
- readiness and health checks
- structured logs for:
  - auth failures
  - job creation
  - queueing failures
  - pipeline phase transitions
  - external source failures
  - synthesis failures
- basic monitoring/alerting for failed jobs and auth issues

### Required documentation

- production runbook
- startup checklist
- credential checklist
- troubleshooting notes for:
  - Firebase auth failures
  - OpenRouter failures
  - queue/worker failures
  - missing optional credentials like IEEE

## Completion Milestones

### Milestone 1: Runtime Ready

- required frontend and backend credentials documented
- Firebase Admin backend auth path verified
- environment examples and setup docs updated

### Milestone 2: Truthful Workspace

- API exposes domain, format, progress, and evidence metadata
- workspace explainability and evidence surfaces are real, not placeholders

### Milestone 3: Release Confidence

- frontend tests added
- backend regressions still green
- browser E2E coverage for happy and failure paths

### Milestone 4: Production Launch Ready

- deployment and runbook complete
- logging/health checks in place
- integrated branch is clean and verified

## Recommended Execution Order

1. Track A: Secrets and runtime readiness
2. Track B: API contract expansion
3. Frontend wiring to new workspace/report payloads
4. Track C: Quality gates
5. Track D: Deployment and operations

## Known Credential Position

### Available now

- frontend Firebase web config
- `OPENROUTER_API_KEY`

### Missing or not yet confirmed

- Firebase Admin backend credentials or equivalent production auth initialization
- `IEEE_API_KEY` (optional)

## Risks

- The product can appear visually ready before the authenticated backend path is actually production-configured.
- Without API contract expansion, the new UI remains a polished shell rather than a complete research workspace.
- Without at least one real end-to-end test, release confidence would still depend too heavily on manual checks.
- Deployment could fail late if Firebase Admin auth, worker runtime, or proxy/CORS assumptions are not verified early.

## Recommendation

Treat production readiness as one final execution project with the API contract expansion as the center of gravity. Meridian is closest to completion when the frontend can actually surface the backend intelligence it already computes, backed by real credentials, real tests, and real deployment documentation.
