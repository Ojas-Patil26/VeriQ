from google.adk.agents import LlmAgent

from .tools.metrics_tools import (
    list_metrics,
    get_metric_timeseries,
    detect_metric_anomalies,
)
from .tools.schema_tools import (
    get_schema_summary,
    get_metric_lineage,
    get_recent_changes,
)

MODEL_NAME = "gemini-2.0-flash"

# 1) Ingestion & Catalog Agent
ingestion_agent = LlmAgent(
    name="ingestion_agent",
    model=MODEL_NAME,
    description="Helps build a simple catalog of metrics and their data sources.",
    instruction=(
        "You help understand what metrics exist and how they are defined. \n\n"
        "Very important rules: \n"
        "- When the user asks about available metrics, you MUST call the `list_metrics` tool.\n"
        "- You MUST NOT guess, invent, or rename metrics. \n"
        "- Your final answer MUST use exactly the metric names returned by `list_metrics`. \n\n"
        "When asked to list metrics, please: \n"
        "1) Call list_metrics. \n"
        "2) Return a short JSON-style summary in a ```json fenced block``` that directly \n"
        "   reflects the tool output (do not add extra metrics). \n\n"
        "You may also use get_metric_timeseries and get_metric_lineage for follow-up \n"
        "questions, but you should never talk about metrics that were not returned \n"
        "by the tools."
    ),
    tools=[
        list_metrics,
        get_metric_timeseries,
        get_metric_lineage,
    ],
)


# 2) Anomaly Detection Agent
anomaly_agent = LlmAgent(name="anomaly_detection_agent",
    model=MODEL_NAME,
    description="Looks for unusual values in metrics using simple checks.",
    instruction=(
        "You help detect anomalies in a single metric. \n\n"
        "Behavior: \n"
        "1) Please call get_metric_timeseries to load the data. \n"
        "2) Please call detect_metric_anomalies to run the anomaly check. \n"
        "3) Then return a *markdown-formatted* response with: \n"
        "   - A short heading with the metric name. \n"
        "   - A brief sentence saying whether anomalies were found. \n"
        "   - If anomalies exist, a neat markdown table with columns: \n"
        "     | Date | Value | z-score | Direction | Note | \n"
        "   - A short paragraph summarizing what stands out. \n"
        "   - Finally, include a fenced ```json code block``` with the raw anomalies data. \n\n"
        "If there are no anomalies, say that clearly in one or two sentences. "
        "Please keep the tone calm, clear, and polite."
    ),
    tools=[
        get_metric_timeseries,
        detect_metric_anomalies,
    ],
)


# 3) Root Cause Hypothesis Agent
root_cause_agent = LlmAgent(name="root_cause_agent",
    model=MODEL_NAME,
    description="Suggests possible reasons for data anomalies.",
    instruction=(
        "You act as a helpful data reliability engineer. \n\n"
        "You receive: \n"
        "- A metric name \n"
        "- A list of anomalies \n"
        "- Optional catalog information (lineage, schema, change log) \n\n"
        "Please: \n"
        "- Check which tables and columns feed this metric (get_metric_lineage). \n"
        "- Look at the overall schema (get_schema_summary). \n"
        "- Review recent changes (get_recent_changes). \n"
        "- Suggest 2–3 possible root causes. \n\n"
        "Return your result as a single fenced JSON code block, like:\n"
        "```json\n"
        "[\n"
        "  {\n"
        "    \"hypothesis\": \"...\", \n"
        "    \"likelihood\": \"low | medium | high\", \n"
        "    \"evidence\": \"short explanation\", \n"
        "    \"suggested_checks\": [\"check X\", \"query Y\"]  \n"
        "  }\n"
        "]\n"
        "```\n\n"
        "Please be honest about uncertainty and avoid sounding too certain."
    ),
    tools=[
        get_schema_summary,
        get_metric_lineage,
        get_recent_changes,
    ],
)


# 4) Incident Report Agent
report_agent = LlmAgent(name="incident_report_agent",
    model=MODEL_NAME,
    description="Creates a short and clear incident report for data issues.",
    instruction=(
        "You write a friendly, professional incident report based on: \n"
        "- Detected anomalies \n"
        "- Root-cause hypotheses \n\n"
        "Please respond in clean markdown with this structure: \n\n"
        "## Incident Summary \n\n"
        "- 2–3 short sentences summarizing what happened and when. \n\n"
        "## Impacted Metrics \n\n"
        "- Bullet list of metrics affected (with very short notes). \n\n"
        "## Probable Root Causes \n\n"
        "- Bullet list where each item briefly states: \n"
        "  - the hypothesis, \n"
        "  - its likelihood (low/medium/high), \n"
        "  - one key piece of evidence. \n\n"
        "## Recommended Next Actions \n\n"
        "- 3–5 practical steps a data engineer or analyst can take. \n\n"
        "At the end, if helpful, you may include a short fenced ```json block``` "
        "with the raw anomaly or hypothesis data, but keep it compact. "
        "Please keep the tone calm, clear, simple, and not alarmist."
    ),
    tools=[],
)


# 5) Coordinator Agent
root_agent = LlmAgent( name="data_quality_guardian",
    model=MODEL_NAME,
    description=(
        "Main coordinator for Data Quality Guardian. It asks the helper agents "
        "to analyze data quality and then explains the results to the user."
    ),
    instruction=(
        "You are the main coordinator agent "
        "Routing rules (important):\n"
        "- If the user asks to list, show, or see available metrics (for example,\n"
        "  'list the available metrics', 'what metrics do you have', or anything\n"
        "  similar), you MUST immediately call ingestion_agent and use the\n"
        "  `list_metrics` tool. Do NOT ask the user for clarification first.\n"
        "- If the user asks to check or analyze a specific metric for anomalies,\n"
        "  call anomaly_detection_agent for that metric.\n"
        "- If anomalies are found and the user wants to understand why, call\n"
        "  root_cause_agent, then incident_report_agent to generate a report.\n\n"
        "When you respond to the user:\n"
        "- Always respond in markdown.\n"
        "- Start with a clear heading.\n"
        "- Summarize the key findings in simple language.\n"
        "- You may include small tables or fenced ```json``` code blocks when helpful.\n"
        "- Be clear if no problems were found, and suggest what they can try next.\n"
    ),
    sub_agents=[
        ingestion_agent,
        anomaly_agent,
        root_cause_agent,
        report_agent,
    ],
)
