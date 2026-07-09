# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repository.

## What this is

**VeriQ** — a multi-agent data quality assistant. A FastAPI backend wraps a
Google ADK (Agent Development Kit) + Gemini agent pipeline that monitors KPI
time series, detects anomalies with a rolling z-score, hypothesizes root
causes, and writes incident reports. A React dashboard (`frontend/`) provides
charts, health cards, CSV upload, an automated PDF report download, and a
streaming chat interface to the agents.

## Commands

### Backend (Python 3.13, `venv/`)
```bash
source venv/bin/activate
pip install -r requirements.txt          # pinned deps
python api.py                            # serves on :8080 (or $PORT)
```
Requires `GOOGLE_API_KEY` in `.env` (see `.env.example`). The process exits at
startup if it is missing.

### Frontend (`frontend/`, Vite + React 19)
```bash
cd frontend
npm install
npm run dev      # :5173, proxies /api and /health to :8080 (no CORS needed in dev)
npm run build    # production bundle in frontend/dist
```

### Agents directly (no web layer)
`adk run VeriQ` or `adk web` from the parent directory.

## Architecture

- **`agent.py`** — all five agents. `data_quality_guardian` (root coordinator)
  delegates to four sub-agents: `ingestion_agent` (metric catalog/lineage),
  `anomaly_detection_agent`, `root_cause_agent`, `incident_report_agent`.
- **`tools/metrics_tools.py`** — `list_metrics` (numeric columns only),
  `get_metric_timeseries`, `detect_metric_anomalies` (time-based rolling
  window, current point excluded via `shift(1)`, zero-std and non-numeric
  guards). Tools return `{"status": "success"|"error", ...}` dicts — they must
  never raise for bad user data.
- **`tools/schema_tools.py`** — schema summary / lineage / recent changes.
  Uses `data/schema_sample.json` + `data/changelog_sample.json` for the sample
  dataset; auto-infers schema from CSV structure for uploads.
- **`tools/data_manager.py`** — active data source state (uploaded CSV vs
  bundled sample), shared `read_csv` (coerces bad dates, drops unparseable
  rows), `detect_date_column`.
- **`report.py`** — deterministic PDF report (fpdf2 + matplotlib Agg, no LLM
  call): per-metric charts with anomaly markers, anomaly tables, column health.
- **`api.py`** — FastAPI app. JSON endpoints under `/api/*` (`metrics`,
  `timeseries`, `anomalies`, `summary`, `upload`, `report/pdf`), `/health`,
  and `POST /api/chat` which streams SSE where each `data:` payload is JSON
  (`{"text": ...}` or `{"error": ...}`), terminated by `data: [DONE]`.
- **`frontend/src/`** — `api.js` (client incl. SSE parser), `App.jsx`
  (state/orchestration), `components/` (TopBar, HealthCards, MetricChart,
  AnomalyTable, ChatPanel). Charts are Recharts; chat markdown is
  react-markdown + rehype-highlight.
- **`data/`** — bundled sample dataset, used as fallback when nothing is
  uploaded.

## Data layer rules

- Fully dynamic: any CSV with a date column (`date`/`timestamp`/`time`/
  `datetime`/`dt`) plus numeric columns works. Non-numeric columns are not
  metrics. No hardcoded metric names anywhere.
- Uploads go through `POST /api/upload` (CSV-only, 10 MB cap, parse-validated,
  temp file cleaned up on replacement/reset).

## Constraints

- **Do not rename agents or change tool function signatures** — ADK and the
  agent instructions depend on them.
- **`GOOGLE_API_KEY`** is the only required env var. Optional:
  `CORS_ORIGINS` (comma-separated allowed origins, default
  `http://localhost:5173`), `PORT` (default 8080). Frontend prod builds use
  `VITE_API_URL`.
- Detector defaults are part of the product's spec: 14-day window,
  |z| ≥ 2.0, both user-adjustable in the UI and API.

## Deployment model

Split deploy: backend container (Dockerfile, `railway.toml`) on Railway;
frontend static build on Vercel (`frontend/vercel.json`) with `VITE_API_URL`
pointing at the Railway URL and `CORS_ORIGINS` on Railway set to the Vercel
URL. See README for step-by-step instructions.
