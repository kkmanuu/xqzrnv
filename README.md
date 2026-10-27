# UK Wind Forecast & Day-Ahead Procurement Dashboard (Pilot)

> **AI assistance:** This project was developed with the assistance of AI tools (Claude by Anthropic, and ChatGPT by OpenAI) for research, implementation support and documentation. The author reviewed the code and methodology.

## Live Application

| | |
|---|---|
| Dashboard | https://frontend-kkmanuus-projects.vercel.app |
| Backend API | https://xqzrnv.onrender.com |
| API documentation | https://xqzrnv.onrender.com/docs |
| Repository | https://github.com/kkmanuu/xqzrnv |
| Demo video | https://youtu.be/vlasWJR6Ksk|

> The backend runs on a free Render instance that sleeps when idle. The first request can take 30-60 seconds; open `/api/health` first to wake it.

## 1. Overview

A UK energy utility buys electricity in the GB day-ahead market one day before delivery. Wind output depends on the weather, so the buyer has to rely on wind forecasts published *before* the decision deadline. This pilot helps the procurement team:

1. See which wind forecast was available at the day-ahead decision cutoff.
2. Compare that forecast with actual national wind generation.
3. Quantify historical forecast error (MAE, RMSE, bias, MAPE).
4. Explore an illustrative procurement scenario using the measured error.

**Scope:** national wind generation, Elexon BMRS data only, delivery periods in January 2026.

### Features

- **Publication inspector:** lists every forecast publication for a delivery day and tags the one usable at the cutoff ("used for decision"), the latest one ("latest now"), and those published too late ("after cutoff").
- **Overview:** accuracy KPIs, forecast vs actual chart and forecast error over time.
- **Accuracy:** error by hour of day (UK local time) and by delivery day.
- **Data table:** sortable, paged table of delivery time, forecast publication time, forecast, actual and error.
- **Procurement scenario:** clearly labelled hypothetical scenario using user-entered demand and other-supply values.
- **Configurable cutoff and basis:** choose the decision cutoff, and compare "known at cutoff" against "latest published (hindsight)".

## 2. Results and Verification

### Headline results

January 2026 delivery periods, forecast known at the 09:20 UK cutoff on D-1, 744 matched periods:

| Metric | Value |
|---|---|
| MAE | 2,127 MW |
| RMSE | 2,606 MW |
| Bias (forecast - actual) | +1,851 MW |
| MAPE | 22.2% (744 of 744 periods used) |
| Mean forecast | 13,433 MW |

Forecasts ran higher than actual generation on average. The cause of this consistent positive bias has not been investigated; scope differences between the WINDFOR and FUELHH datasets are one possibility.

### Verification

| Check | Result |
|---|---|
| Frontend (Vercel) and backend (Render) | Deployed and working end to end |
| Docker Compose | `docker compose up --build` builds and runs both services |
| Data | Real Elexon FUELHH and WINDFOR data for January 2026, cached in `backend/app/data/cache` |
| Frontend build | `npm run build` (type-check and production build) runs as part of the Docker image build |
| Backend tests | `cd backend && pytest -q` |

Automated tests use small synthetic fixtures. Synthetic data is never shown in the dashboard.

## 3. Data Sources

All data comes from the keyless Elexon Insights API (`https://data.elexon.co.uk/bmrs/api/v1`).

**Actual generation: FUELHH** ([docs](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream))
Filtered to `fuelType = WIND`. Fields used: `startTime` (target period), `generation` (MW).

**Forecast generation: WINDFOR** ([docs](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream))
Fields used: `startTime`, `publishTime` (when the forecast was created), `generation` (MW).

Requests are made in one-day chunks with timeouts and retries. Forecasts for early-January delivery are published before 1 January, so forecast retrieval starts a few days earlier. Records are normalised to UTC, de-duplicated and validated, then written to a CSV cache so dashboard use never calls Elexon live.

WINDFOR is published at hourly resolution, so matched periods in the analysis are hourly.

## 4. Methodology

### 4.1 Forecast selection at decision time

For each delivery period, with $D$ the UK-local delivery date and $t_c$ the cutoff on day $D-1$, the selected forecast is the record with the latest publication time $t_p$ such that:

$$t_p \le t_c$$

Forecasts published after the cutoff are never used in the decision-time analysis. Cutoffs are interpreted in `Europe/London` wall-clock time, so daylight-saving changes are handled (covered by unit tests). The app also shows the latest published forecast separately for comparison.

### 4.2 Cutoff assumption

The default cutoff is **09:20 UK time on D-1**, which is configurable (`DEFAULT_CUTOFF_LOCAL` and the UI selector). Public exchange timings:

| Auction | Gate closure (UK time, D-1) |
|---|---|
| EPEX GB hourly day-ahead | 09:20 |
| N2EX hourly day-ahead | 09:50 |
| EPEX GB half-hourly day-ahead | 15:30 |

09:20 is the earliest hourly gate, so it is the most conservative choice. These are public exchange timings, not any specific client's trading rules, and should be confirmed with the client.

### 4.3 Matching

Forecasts and actuals are inner-joined on `startTime` (UTC). Unmatched periods are excluded from the metrics and reported as a warning, never treated as zero.

### 4.4 Metrics

All values are in MW. The error for each matched period is forecast minus actual:

$$e_i = \hat{y}_i - y_i$$

| Metric | Definition | Meaning |
|---|---|---|
| MAE | $\frac{1}{n}\sum \lvert e_i \rvert$ | Average size of the miss |
| RMSE | $\sqrt{\frac{1}{n}\sum e_i^2}$ | Like MAE, but penalises large misses more |
| Bias | $\frac{1}{n}\sum e_i$ | Positive = forecasts ran high (wind over-promised) |
| MAPE | $\frac{100}{m}\sum \lvert e_i / y_i \rvert$ | Percentage error, only for periods with actual $\ge$ 100 MW |

MAPE excludes near-zero actuals because the percentage is meaningless there; the number of periods used is shown. Metrics are historical summaries, not guarantees of future performance.

### 4.5 Procurement scenario

The additional power to buy depends on demand minus wind and all other supply. No demand data is in scope, so the app **does not** compute the real requirement. The scenario page takes demand and other-supply values typed by the user, labels all results hypothetical, and applies the historical P10 and P90 forecast error to the mean wind forecast. Wind forecast error alone is not the amount to buy.

## 5. Architecture

```text
React + TypeScript (Vite, Bootstrap 5, Recharts)   [Vercel]
                    |
                    |  HTTP / JSON
                    v
FastAPI + pandas (routes, validation, services)    [Render, Docker]
                    |
                    v
CSV data cache  <---- built from ----  Elexon Insights API (FUELHH, WINDFOR)
```

**Stack:** React, TypeScript, Vite, Bootstrap 5, Recharts; Python, FastAPI, pandas, NumPy, HTTPX, Pydantic Settings, tenacity, pytest, respx; Docker and Docker Compose.

**Data flow:** fetch from Elexon, normalise and validate, cache to CSV, select the forecast at the cutoff, match to actuals, compute metrics, return JSON to the frontend.

## 6. API

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Health check |
| `GET /api/meta` | Date window, cutoff presets, data freshness, record counts |
| `GET /api/actuals?from&to` | Actual wind generation for a date range |
| `GET /api/forecasts?date&mode&cutoff[&publish_time]` | Forecast for a delivery day (`asof`, `latest`, or one publication) |
| `GET /api/forecast-publications?date&cutoff` | All publications for a day, flagged against the cutoff |
| `GET /api/analysis?from&to&mode&cutoff` | Metrics, by-hour and by-day breakdowns, matched rows |

Errors: `422` for invalid parameters (dates outside the pilot window, bad cutoff format), `503` when Elexon is unavailable and no cache exists. Interactive docs are at `/docs`.

## 7. Repository Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/routes.py            API endpoints
│   │   ├── services/
│   │   │   ├── elexon_client.py     Elexon HTTP client (chunking, retries)
│   │   │   ├── normalise.py         validation, de-duplication, WIND filter
│   │   │   ├── selection.py         D-1 cutoff (DST-aware), selection, matching
│   │   │   ├── metrics.py           MAE, RMSE, bias, MAPE
│   │   │   └── store.py             cache build and load
│   │   ├── config.py                environment-driven settings
│   │   └── main.py                  FastAPI app and CORS
│   ├── scripts/snapshot.py          fetch January 2026 data into the cache
│   ├── tests/                       pytest suite (synthetic fixtures)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── views/                   Overview, Inspector, Accuracy, DataTable, Scenario
│   │   ├── api.ts                   typed API client
│   │   └── App.tsx                  layout, filters, state
│   ├── Dockerfile
│   └── vite.config.ts
├── docker-compose.yml
├── .env.example
└── README.md
```

## 8. Running Locally

**Prerequisites:** Python 3.11+, Node.js 20+, internet access to Elexon, and Docker if using Compose.

### Configure

```bash
cp .env.example .env            # Windows: Copy-Item .env.example .env
```

No secrets are needed; the Elexon Insights API is keyless.

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate       # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m scripts.snapshot      # fetches Jan 2026 data into app/data/cache
uvicorn app.main:app --reload
```

Health check: http://localhost:8000/api/health

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The dev server proxies `/api` to the backend on port 8000.

### Docker Compose

```bash
docker compose up --build
```

Open http://localhost:3000 (frontend) and http://localhost:8000/api/health (backend). Port 8000 must be free.

### Tests

```bash
cd backend && pytest -q
cd frontend && npm run build
```

## 9. Configuration

| Variable | Purpose | Default |
|---|---|---|
| `ELEXON_BASE_URL` | Elexon Insights API base URL | `https://data.elexon.co.uk/bmrs/api/v1` |
| `HTTP_TIMEOUT_S`, `HTTP_RETRIES` | Request timeout and retry count | `30`, `3` |
| `CHUNK_DAYS` | Days per Elexon request | `1` |
| `CACHE_DIR` | Cache location | `app/data/cache` |
| `DEFAULT_CUTOFF_LOCAL` | Day-ahead cutoff, UK time (HH:MM) | `09:20` |
| `CORS_ORIGINS` | Comma-separated allowed browser origins | localhost origins |
| `WINDOW_START`, `WINDOW_END` | Pilot delivery window | `2026-01-01`, `2026-01-31` |
| `VITE_API_BASE_URL` | Backend URL, baked into the frontend at build time | empty (uses proxy) |

## 10. Deployment

**Frontend (Vercel):** root directory `frontend`, framework Vite, environment variable `VITE_API_BASE_URL=https://xqzrnv.onrender.com`. Redeploy after changing it, because Vite embeds it at build time.

**Backend (Render):** Docker runtime, root directory `backend`, health check path `/api/health`, and `CORS_ORIGINS` set to the exact Vercel origin. The January 2026 cache is committed to the repository, so the backend serves data immediately without re-fetching from Elexon.

**Troubleshooting**

| Symptom | Likely cause |
|---|---|
| CORS error in the browser console | `CORS_ORIGINS` does not match the Vercel origin exactly (check `https` and trailing slash) |
| Dashboard cannot reach the API | `VITE_API_BASE_URL` unset or changed without a redeploy |
| Empty dashboard or zero counts | Cache files missing; run `python -m scripts.snapshot` and check `/api/meta` |
| First load very slow | Free Render instance was asleep |
| `503` responses | Elexon unreachable and no cache available |

## 11. Limitations and Assumptions

- National wind generation and January 2026 delivery periods only.
- No demand, other-generation or price data, so the real procurement requirement and the cost of forecast error cannot be calculated.
- The procurement scenario is illustrative and depends on user-entered assumptions.
- The default cutoff is a configurable assumption based on public exchange timings and must be confirmed against the client's actual process.
- Historical accuracy does not guarantee future performance.
- The positive forecast bias is reported but its cause has not been investigated.

## 12. Possible Next Steps

- Extend to further delivery months and scheduled cache refreshes.
- Add client-specific decision deadlines.
- Add forecast accuracy by forecast horizon.
- Incorporate demand and other-supply data to size the real procurement requirement.
- Add monitoring for data freshness and missing delivery periods.

---

*This is a technical pilot for evaluation. Results should be validated against authoritative market data and the client's operational requirements before being used for procurement decisions.*