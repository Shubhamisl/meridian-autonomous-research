# Meridian Deployment Checklist

## Secrets and configuration

- `OPENROUTER_API_KEY` is present in the backend runtime environment.
- `GOOGLE_APPLICATION_CREDENTIALS` or ADC is configured for the backend host.
- `IEEE_API_KEY` is set only if IEEE access is required; it remains optional.
- All six frontend Firebase web env values are set for real production login.
- `VITE_E2E_TESTING` is not set in production.

## Runtime services

- The frontend is deployed and serving the built artifact.
- The FastAPI API is reachable from the frontend origin.
- The Celery worker is running with the same application version as the API.
- The API and worker share the same persistent storage for the SQLite-backed data files.
- Any overridden Celery broker or result backend is reachable from the worker.

## Routing and security

- CORS or reverse-proxy rules allow the frontend origin to call the API.
- The frontend cannot access protected routes without a valid Firebase-authenticated session.
- Firebase authorized domains include the production frontend domain.
- Production logs do not expose tokens, private keys, or full Firebase service account payloads.

## Functional verification

- `GET /health` returns `{"status":"ok"}` from the API.
- A real browser can open `/login` and reach the correct configured or setup state.
- A signed-in user can create a research job from the dashboard.
- A completed workspace can render the report body, evidence cards, and explainability panel.
- The worker can process at least one real or fully mocked end-to-end research job without manual intervention.

## Pre-launch validation

- Run `npm run test` in `frontend/`.
- Run `npm run lint` in `frontend/`.
- Run `npm run build` in `frontend/`.
- Run `npx playwright test` in `frontend/`.
- Verify the API health check and one completed workspace in the browser.

## Rollback checklist

- Keep the previous frontend build artifact available.
- Keep the previous backend image or release tag available.
- Confirm the SQLite data volume is backed up before switching releases.
- Confirm the worker can be stopped cleanly before rolling back the API.
