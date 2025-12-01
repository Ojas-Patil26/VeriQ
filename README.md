# Data Quality Guardian

Data Quality Guardian is a small multi-agent system that helps monitor simple
analytics metrics, detect anomalies, and suggest possible root causes. It is
built for the Google AI Agents Intensive capstone.

## How it works

- **Ingestion agent**: understands available metrics and their lineage.
- **Anomaly detection agent**: looks for unusual values in a chosen metric.
- **Root cause agent**: suggests possible reasons for anomalies.
- **Incident report agent**: creates a short, clear incident report.

All agents are coordinated by a main `data_quality_guardian` root agent.

## Setup

1. Create and activate a virtual environment (optional but recommended).
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
