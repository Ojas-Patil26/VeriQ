# VeriQ – Intelligent Data Quality Agent

VeriQ is a multi-agent data quality assistant that monitors product metrics, detects anomalies, and suggests likely root causes. It is built with the Google Agent Development Kit (ADK) and Gemini models as part of the **Google AI Agents Intensive (Nov 10–14, 2025) Capstone Project**.

> **Track fit:** Enterprise Agents / Agents for Good  
> **Core idea:** Help teams trust their dashboards by catching data issues early and explaining *why* they happened.

---

## 1. Problem & Motivation

Modern products rely heavily on dashboards and analytics to drive decisions. But:

- Pipelines break silently.
- Schema changes ripple through metrics.
- Dashboards look “off” and no one knows why.
- Engineers lose hours manually checking queries, logs, and recent changes.

This creates **hidden risk**: leaders may make decisions based on incorrect or stale data.

**VeriQ** addresses this by acting as a *data quality co-pilot*:  
it continuously inspects metrics, flags unusual behavior, and suggests plausible root causes using schema and changelog context.

---

## 2. Solution Overview

VeriQ is implemented as a **multi-agent system** on top of the ADK:

- A **root coordinator agent** (`data_quality_guardian`) that talks to the user and orchestrates sub-agents.
- Specialized sub-agents for:
  - Metric catalog & lineage
  - Anomaly detection
  - Root-cause hypothesis generation
  - Human-readable incident reporting

Under the hood, agents use **structured tools** that read from:

- A synthetic **metrics time series** (`data/metrics_sample.csv`)
- A simple **schema & lineage description** (`data/schema_sample.json`)
- A **change log** with recent schema/pipeline changes (`data/changelog_sample.json`)

This design mirrors a realistic analytics environment (e.g., a startup’s product metrics), but using lightweight local files for the capstone.

---

## 3. Key Features (Course Concepts)

VeriQ demonstrates several concepts from the AI Agents Intensive:

- ✅ **Multi-agent architecture**
  - Root coordinator + 4 specialized LLM agents.
- ✅ **Tools**
  - Custom tools for metrics, schema, and changelog access:
    - `list_metrics`, `get_metric_timeseries`, `detect_metric_anomalies`
    - `get_schema_summary`, `get_metric_lineage`, `get_recent_changes`
- ✅ **Context / structured outputs**
  - Agents return structured JSON-like data where useful (e.g. anomaly lists, hypotheses).
- ✅ **Clear separation of concerns**
  - Each agent has a focused responsibility, making it easy to extend (e.g. adding evaluation, memory, or deployment later).

You can extend this base to add:

- Sessions & memory
- Observability & logging
- Agent evaluation
- Cloud deployment (Cloud Run / Agent Engine)

---

## 4. Architecture

### 4.1 Agent Roles

All agents live in `agent.py`.

|         Agent Name        |                      Role                                         |
|---------------------------|-------------------------------------------------------------------|
| `data_quality_guardian`   | Root agent (VeriQ coordinator) – user-facing, orchestrates others |
| `ingestion_agent`         | Lists metrics, inspects basic metric + lineage context            |
| `anomaly_detection_agent` | Runs anomaly detection on a single metric                         |
| `root_cause_agent`        | Proposes likely root causes using schema + changelog              |
| `incident_report_agent`   | Turns findings into a clean incident report                       |

### 4.2 Tools

Tools live under `tools/`.

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
