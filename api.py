"""VeriQ web API.

FastAPI layer wrapping the ADK multi-agent pipeline. Serves JSON endpoints
for the React dashboard (frontend/) plus a streaming chat endpoint and an
automated PDF data quality report.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import tempfile

from dotenv import load_dotenv

load_dotenv()

if not os.environ.get("GOOGLE_API_KEY"):
    logging.basicConfig(level=logging.ERROR)
    logging.error(
        "GOOGLE_API_KEY is not set. "
        "Create a .env file with GOOGLE_API_KEY=<your-key> or export it."
    )
    sys.exit(1)

from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# agent.py uses relative imports, so the package's parent must be on sys.path.
_project_dir = Path(__file__).resolve().parent
_parent_dir = _project_dir.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

_pkg_name = _project_dir.name
import importlib
_agent_mod = importlib.import_module(f"{_pkg_name}.agent")
_tools_dm = importlib.import_module(f"{_pkg_name}.tools.data_manager")
_tools_mt = importlib.import_module(f"{_pkg_name}.tools.metrics_tools")
_report_mod = importlib.import_module(f"{_pkg_name}.report")

_root_agent = _agent_mod.root_agent
get_data_source = _tools_dm.get_data_source
set_data_source = _tools_dm.set_data_source
reset_to_sample = _tools_dm.reset_to_sample
is_using_sample = _tools_dm.is_using_sample
read_csv = _tools_dm.read_csv
detect_date_column = _tools_dm.detect_date_column
DataReadError = _tools_dm.DataReadError
list_metrics = _tools_mt.list_metrics
get_metric_timeseries = _tools_mt.get_metric_timeseries
detect_metric_anomalies = _tools_mt.detect_metric_anomalies
build_pdf_report = _report_mod.build_pdf_report

APP_NAME = "veriq"
USER_ID = "web_user"

DEFAULT_WINDOW = 14
DEFAULT_Z = 2.0

app = FastAPI(title="VeriQ", version="1.0.0")

# The dashboard is served from a different origin (Vite dev server locally,
# Vercel in production), so cross-origin requests must be allowed explicitly.
_cors_origins = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

session_service = InMemorySessionService()
runner = Runner(
    agent=_root_agent,
    app_name=APP_NAME,
    session_service=session_service,
)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    session_id: str = Field(min_length=1, max_length=64)


@app.get("/")
async def index():
    return {
        "service": "VeriQ API",
        "docs": "/docs",
        "health": "/health",
        "endpoints": [
            "/api/metrics",
            "/api/timeseries",
            "/api/anomalies",
            "/api/summary",
            "/api/upload",
            "/api/chat",
            "/api/report/pdf",
        ],
    }


@app.get("/health")
async def health():
    return {"status": "ok", "data_source": str(get_data_source())}


@app.get("/api/metrics")
def metrics():
    return list_metrics()


@app.get("/api/timeseries")
def timeseries(metric: str = Query(min_length=1, max_length=200)):
    return get_metric_timeseries(metric)


@app.get("/api/anomalies")
def anomalies(
    metric: str = Query(min_length=1, max_length=200),
    window: int = Query(default=DEFAULT_WINDOW, ge=2, le=90),
    z: float = Query(default=DEFAULT_Z, ge=0.5, le=10.0),
):
    return detect_metric_anomalies(metric, window_size=window, z_threshold=z)


@app.get("/api/summary")
def summary(
    window: int = Query(default=DEFAULT_WINDOW, ge=2, le=90),
    z: float = Query(default=DEFAULT_Z, ge=0.5, le=10.0),
):
    """Dataset health overview for the dashboard cards."""
    try:
        df = read_csv(parse_dates=True)
    except DataReadError as e:
        return {"status": "error", "message": str(e)}

    date_col = detect_date_column(df)
    date_range = None
    if date_col is not None and len(df) > 0:
        date_range = {
            "start": df[date_col].min().date().isoformat(),
            "end": df[date_col].max().date().isoformat(),
        }

    listing = list_metrics()
    metric_names = listing.get("metrics", []) if listing.get("status") == "success" else []

    anomaly_counts = {}
    for m in metric_names:
        result = detect_metric_anomalies(m, window_size=window, z_threshold=z)
        anomaly_counts[m] = result.get("n_anomalies", 0) if result.get("status") == "success" else 0

    columns = {
        col: {
            "dtype": str(df[col].dtype),
            "null_count": int(df[col].isna().sum()),
        }
        for col in df.columns
    }

    source = get_data_source()
    display_name = _current_upload_name or source.name
    return {
        "status": "success",
        "source": {"name": display_name, "is_sample": is_using_sample()},
        "rows": len(df),
        "date_column": date_col,
        "date_range": date_range,
        "metrics": metric_names,
        "columns": columns,
        "anomaly_counts": anomaly_counts,
        "total_anomalies": sum(anomaly_counts.values()),
        "window_size": window,
        "z_threshold": z,
    }


MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
_current_upload: Path | None = None
_current_upload_name: str | None = None


def _cleanup_previous_upload() -> None:
    """Delete the previous uploaded temp file so temp files don't accumulate."""
    global _current_upload, _current_upload_name
    if _current_upload is not None:
        try:
            _current_upload.unlink(missing_ok=True)
        except OSError:
            pass
        _current_upload = None
    _current_upload_name = None


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    global _current_upload, _current_upload_name

    # Only accept CSV files
    suffix = Path(file.filename or "upload.csv").suffix.lower()
    if suffix != ".csv":
        raise HTTPException(status_code=400, detail="Only .csv files are accepted.")

    # Enforce a size limit to prevent memory/disk exhaustion
    contents = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB).")
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file.")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
    tmp.write(contents)
    tmp.close()
    tmp_path = Path(tmp.name)

    # Validate that the file actually parses as CSV before accepting it
    try:
        pd.read_csv(tmp_path, nrows=5)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="File could not be parsed as CSV.")

    _cleanup_previous_upload()
    _current_upload = tmp_path
    _current_upload_name = file.filename or "upload.csv"
    set_data_source(tmp_path)
    return {"status": "ok", "filename": file.filename, "metrics": list_metrics()}


@app.delete("/api/upload")
async def delete_upload():
    reset_to_sample()
    _cleanup_previous_upload()
    return {"status": "ok"}


@app.get("/api/report/pdf")
def report_pdf(
    window: int = Query(default=DEFAULT_WINDOW, ge=2, le=90),
    z: float = Query(default=DEFAULT_Z, ge=0.5, le=10.0),
):
    """Generate and download the automated data quality report as a PDF."""
    try:
        pdf_bytes = build_pdf_report(window_size=window, z_threshold=z)
    except DataReadError as e:
        raise HTTPException(status_code=400, detail=str(e))
    filename = f"veriq-report-{pd.Timestamp.utcnow().date().isoformat()}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/chat")
async def chat(req: ChatRequest):
    session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=req.session_id,
    )
    if session is None:
        session = await session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=req.session_id,
        )

    content = types.Content(
        role="user", parts=[types.Part(text=req.message)]
    )

    async def event_stream():
        # Each SSE data payload is a JSON object so newlines in the agent's
        # markdown survive the line-based SSE framing.
        try:
            async for event in runner.run_async(
                user_id=USER_ID,
                session_id=session.id,
                new_message=content,
            ):
                if not event.content or not event.content.parts:
                    continue
                if event.get_function_calls() or event.get_function_responses():
                    continue
                for part in event.content.parts:
                    if part.text:
                        yield f"data: {json.dumps({'text': part.text})}\n\n"
        except Exception:
            logging.exception("Agent run failed mid-stream")
            yield f"data: {json.dumps({'error': 'The agent hit an internal error. Please try again.'})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
