# Meridian Production Runbook

## What must be running

Meridian currently depends on four runtime pieces:

- the frontend app
- the FastAPI API
- the Celery worker
- persistent storage for the SQLite databases created by the backend and worker

If you deploy the API and worker in separate containers, they must share the same persistent volume so both processes see the same `meridian.db`, Celery broker DB, and Celery result DB files.

## Required environment variables

### Backend required

- `OPENROUTER_API_KEY`
- `GOOGLE_APPLICATION_CREDENTIALS` or valid Google ADC on the host/container

### Backend optional

- `IEEE_API_KEY`
- `WEB_CREDIBILITY_AUDIT_LIMIT`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`

### Frontend required for real login

- `VITE_FIREBASE_API_KEY`
- `VITE_FIREBASE_AUTH_DOMAIN`
- `VITE_FIREBASE_PROJECT_ID`
- `VITE_FIREBASE_STORAGE_BUCKET`
- `VITE_FIREBASE_MESSAGING_SENDER_ID`
- `VITE_FIREBASE_APP_ID`

### Frontend test-only

- `VITE_E2E_TESTING`

`VITE_E2E_TESTING` must stay disabled in production. It only exists so browser automation can bypass auth in a local test run when a matching localStorage flag is present.

## Start order

1. Start the database file volume or mount.
2. Start the backend API.
3. Start the Celery worker.
4. Start the frontend.

### API

```bash
python -m uvicorn src.meridian.interfaces.api.main:app --host 0.0.0.0 --port 8000
```

### Worker

```bash
celery -A src.meridian.interfaces.workers.app worker --loglevel=info
```

### Frontend development smoke test

```bash
cd frontend
npm ci
npm run dev -- --host 0.0.0.0 --port 4173
```

### Frontend production preview

```bash
cd frontend
npm run build
npm run preview -- --host 0.0.0.0 --port 4173
```

## Auth and Firebase expectations

- Firebase login is the normal production path for the frontend.
- The frontend login screen intentionally shows setup guidance when the Firebase web env is missing or still placeholder text.
- The backend verifies Firebase bearer tokens through Google credentials or ADC.
- If Firebase Admin cannot initialize, the API should fail with a clear 503 rather than pretending auth is healthy.

## Health checks

### API health

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

### Browser smoke checks

- Open `/login` and confirm the setup state appears when Firebase frontend env values are not configured.
- Sign in with a real Firebase user and confirm `/dashboard` loads.
- Open a completed workspace and confirm the report text and evidence cards render.

## Operational checks before release

- Confirm the backend can authenticate a real Firebase token.
- Confirm `/api/research` requests succeed with the production bearer token path.
- Confirm the worker can create and finish a research job.
- Confirm the workspace route can load a completed report in the browser.
- Confirm logs show a clear error if OpenRouter, Firebase Admin, or the queue backend is unavailable.

## Troubleshooting

### Firebase auth failures

- Check `GOOGLE_APPLICATION_CREDENTIALS` or ADC on the API host.
- Check that the frontend Firebase web env matches the correct project.
- Check that the user token was issued by the same Firebase project.

### Worker queue failures

- Confirm the worker process has access to the same SQLite files as the API.
- Confirm `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` are pointing at a reachable backend if you override the defaults.
- Check worker logs for task import or startup errors.

### Missing optional IEEE access

- The product should keep working if `IEEE_API_KEY` is absent.
- Treat IEEE requests as unavailable rather than blocking the rest of the pipeline.

## Release verification

Before a production rollout, run:

```bash
cd frontend
npm run test
npm run lint
npm run build
npx playwright test
```

Only ship if the API health check passes and the completed-workspace browser smoke test passes on the same artifact.
