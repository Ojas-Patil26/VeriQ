# VeriQ – Intelligent Data Quality Agent

VeriQ is a multi-agent data quality assistant that monitors product metrics, detects anomalies, and suggests likely root causes. It is built with the Google Agent Development Kit (ADK) and Gemini models as part of the **Google AI Agents Intensive (Nov 10–14, 2025) Capstone Project**.

> **Track fit:** Enterprise Agents  
> **Core idea:** Help teams trust their dashboards by catching data issues early and explaining *why* they happened.

---

## 1. Problem & Motivation

Modern products rely heavily on dashboards and analytics to drive decisions. But in most real stacks:

- Pipelines break silently.  
- Schema changes ripple through metrics in subtle ways.  
- Dashboards look “off” and no one is sure whether it’s real or a data bug.  
- Engineers lose hours manually checking queries, logs, and recent changes.

This creates **hidden risk**: leaders may make decisions based on incorrect, stale, or incomplete data.

**VeriQ** addresses this by acting as a *data quality co-pilot*:  
it inspects metrics, flags unusual behavior, and suggests plausible root causes using schema and changelog context, all through a conversational interface.

---

## 2. Solution Overview

VeriQ is implemented as a **multi-agent system** on top of the ADK:

- A **root coordinator agent** (`data_quality_guardian`) that:
  - Talks to the user.
  - Routes requests to specialized helper agents.
  - Aggregates their outputs into clean, readable markdown.

- Specialized sub-agents for:
  - Metric catalog & lineage.
  - Anomaly detection.
  - Root-cause hypothesis generation.
  - Human-readable incident reporting.

Under the hood, agents use **structured tools** that read from local demo data:

- A synthetic **metrics time series** – `data/metrics_sample.csv`  
- A simple **schema & lineage description** – `data/schema_sample.json`  
- A **change log** of recent schema / pipeline changes – `data/changelog_sample.json`  

This design mirrors a realistic analytics environment (e.g., a startup’s product metrics) while remaining lightweight and fully local for this capstone.

---

## 3. Key Features (Course Concepts)

VeriQ demonstrates several core concepts from the AI Agents Intensive:

- ✅ **Multi-agent architecture**
  - One root coordinator agent.
  - Four specialized helper agents with focused responsibilities.

- ✅ **Tools**
  - Custom tools for metrics, schema, and changelog access:
    - `list_metrics`, `get_metric_timeseries`, `detect_metric_anomalies`
    - `get_schema_summary`, `get_metric_lineage`, `get_recent_changes`

- ✅ **Context and structured outputs**
  - Tools return structured dicts that agents can reason over.
  - Agents often respond with markdown + optional JSON style snippets for clarity and machine readability.

- ✅ **Separation of concerns**
  - Clear split between:
    - Data layer (CSV/JSON under `data/`)
    - Tools layer (`tools/*.py`)
    - Agent orchestration (`agent.py`)

This base can be extended with:

- Sessions & memory (e.g. remembering past incidents).
- Observability, logging, and evaluation.
- Cloud deployment via Vertex AI Agent Engine or Cloud Run.

---

## 4. Architecture

![VeriQ Architecture](image.png)

### 4.1 Agent Roles

All agents are defined in `agent.py`.

| Agent Name               | Role                                                                 |
|--------------------------|----------------------------------------------------------------------|
| `data_quality_guardian`  | Root agent (VeriQ coordinator); user-facing; orchestrates sub-agents |
| `ingestion_agent`        | Lists metrics; provides time-series and lineage context              |
| `anomaly_detection_agent`| Detects anomalies in a single metric’s time series                   |
| `root_cause_agent`       | Suggests likely root causes using schema + changelog data           |
| `incident_report_agent`  | Produces a clean, readable incident report                          |

#### Root Coordinator: `data_quality_guardian`

- The only agent that talks directly to the user.
- Interprets user intent and decides whether to:
  - List available metrics.
  - Run anomaly detection on a metric.
  - Explore possible root causes.
  - Generate an incident-style summary.

It calls helper agents as sub-agents and hides internal complexity behind a simple conversational experience.

#### `tools/metrics_tools.py`

- `list_metrics()`:  
  Reads `metrics_sample.csv`, returns available metric names.

- `get_metric_timeseries(metric_name, start_date=None, end_date=None)`:  
  Returns a list of `{date, value}` points for the selected metric.

- `detect_metric_anomalies(metric_name, window_size=14, z_threshold=3.0)`:  
  Uses a rolling mean/std to compute z-scores and flags points where  
  `abs(z_score) >= z_threshold`. Returns:
  ```jsonc
  {
    "metric": "daily_active_users",
    "n_anomalies": 1,
    "anomalies": [
      {
        "date": "2025-11-15",
        "value": 600.0,
        "z_score": -3.33,
        "direction": "low"
      }
    ]
  }
