# UK Wind Forecast & Day-Ahead Procurement Dashboard (pilot)

> **AI disclosure:** this project was designed and written with the help of an AI assistant (Claude, Anthropic), as permitted by the assignment. All code should be reviewed by the submitting developer.

## Purpose
A UK utility buys power in the GB day-ahead market on D-1, so it has to rely on wind forecasts published *before* that decision. This app shows (1) which WINDFOR forecast was available at the decision time and (2) how accurate such forecasts have been against FUELHH actuals, so the error can be priced into the buy.

Scope: national wind only, Elexon BMRS data only, delivery periods in **January 2026**.

## Status (read this first)
| Item | State |
|---|---|
| Backend unit + API tests | 14 passed (run in an authoring sandbox with synthetic fixtures) |
| Frontend type-check + production build | passes |
| API smoke test against a **synthetic** cache | passes (cache loading, validation, publication flags) |
| Live Elexon fetch | **NOT yet verified**: the sandbox could not reach `data.elexon.co.uk`. Run `python -m scripts.snapshot` and inspect the output |
| Docker / Docker Compose | **NOT yet run** (no Docker in the authoring sandbox) |
| Vercel + backend deployment | **NOT deployed.** URL: _add after you deploy and verify_ |
| Demo video | _add link_ |

## Methodology
**Forecast selection.** For each half-hour delivery period, the forecast "known at decision time" is the WINDFOR record with the latest `publishTime` that is **<= the cutoff on D-1**, where D is the UK-local delivery date. Cutoff times are interpreted in `Europe/London` wall-clock time, so DST shifts are handled (tested around 29 Mar 2026). The app also shows the "latest available now" forecast, clearly separated, for comparison.

**Cutoff assumption (configurable, default 09:20).** GB hourly day-ahead auctions: EPEX 09:20, N2EX 09:50 (UK time, D-1); the EPEX half-hourly auction closes 15:30. Sources: Nord Pool's N2EX support page (09:50), EPEX SPOT market data (GB closure shown as 10:20 CET = 09:20 UK), Modo Energy's GB market explainer. Default 09:20 is the earliest hourly gate, i.e. the most conservative choice. Confirm your client's actual trading deadline and set `DEFAULT_CUTOFF_LOCAL` / use the UI selector.

**Matching.** Forecasts and actuals are inner-joined on `startTime` (UTC). Unmatched forecast periods are excluded from metrics and surfaced as a warning.

**Metrics (all MW; error = forecast - actual).**
- MAE: mean(|error|). RMSE: sqrt(mean(error^2)), weights large misses more.
- Bias: mean(error). Positive = forecasts run high, i.e. wind was over-promised.
- MAPE: mean(|error| / actual) over periods with actual >= 100 MW only (near-zero actuals make it meaningless); the number of periods used is shown.
- P10/P90 of error are used in the illustrative scenario.

**Procurement scenario.** No demand data is in scope, so the app does **not** compute the real requirement. The scenario page takes user-typed demand and other-supply assumptions, labels everything hypothetical, and applies historical error percentiles to the mean wind forecast.

## Architecture
```
frontend (React+TS+Vite, Bootstrap 5, Recharts) --HTTP/JSON--> backend (FastAPI + pandas)
                                                                  |-- on-disk CSV cache (Jan 2026)
                                                                  '-- Elexon Insights API (keyless)
```
Elexon endpoints used (base `https://data.elexon.co.uk/bmrs/api/v1`): `datasets/FUELHH/stream` (`settlementDateFrom/To`, `fuelType=WIND`) and `datasets/WINDFOR/stream` (`publishDateTimeFrom/To`), requested in 1-day chunks with timeouts and retries. Parameter names were taken from Elexon's published OpenAPI collection; per-request window limits and live response shape still need confirming. Data is fetched once, normalised (UTC, deduplicated, invalid rows dropped) and cached to `backend/app/data/cache`, so dashboard interactions never call Elexon.

### API
`GET /api/health`, `/api/meta` (freshness, presets), `/api/actuals?from&to`, `/api/forecasts?date&mode&cutoff[&publish_time]`, `/api/forecast-publications?date&cutoff`, `/api/analysis?from&to&mode&cutoff`. Errors: 422 invalid params, 503 Elexon unavailable with no cache.

## Directory guide
```
backend/app/config.py                   env-driven settings + logging
backend/app/services/elexon_client.py   HTTP client, chunking, retries
backend/app/services/normalise.py       validation / dedupe / WIND filter
backend/app/services/selection.py       D-1 cutoff (DST-aware), as-of selection, matching
backend/app/services/metrics.py         MAE, RMSE, bias, MAPE
backend/app/services/store.py           cache build/load
backend/app/api/routes.py               endpoints
backend/scripts/snapshot.py             pre-fetch Jan 2026 into the cache
backend/tests/                          pytest (synthetic fixtures; never shown in the app)
frontend/src/views/                     Overview, Inspector, Accuracy, DataTable, Scenario
docker-compose.yml, .env.example        local orchestration and settings
```

## Run locally
```bash
cp .env.example .env
# 1. Pull real data (needs internet access to Elexon). Inspect the counts it prints.
cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
python -m scripts.snapshot
uvicorn app.main:app --reload            # http://localhost:8000/api/health
# 2. Frontend
cd ../frontend && npm install && npm run dev   # http://localhost:5173 (proxies /api)
```
Docker: `docker compose up --build`, then open http://localhost:3000.

Tests: `cd backend && pytest -q`. Frontend check: `cd frontend && npm run build`.

## Deployment
- **Frontend (Vercel):** import the repo, root directory `frontend`, env var `VITE_API_BASE_URL=https://<backend-url>`.
- **Backend:** any container host (Render, Fly.io, Railway). Use `backend/Dockerfile`; it honours `$PORT`. Set `CORS_ORIGINS=https://<your-vercel-app>`. Commit the generated cache files so the first request does not trigger a full Elexon fetch.
- Troubleshooting: browser CORS error -> `CORS_ORIGINS` missing the exact Vercel origin; empty dashboard -> run the snapshot and check counts via `/api/meta`; 503 -> Elexon unreachable from the host.

## Limitations
No demand or other-supply data, so required procurement cannot be computed. January 2026 only. National level only. The cutoff presets reflect public exchange timings, not any specific client's trading rules.
