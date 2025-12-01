from __future__ import annotations

from typing import Dict, Any, Optional
from pathlib import Path
import json

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SCHEMA_FILE = DATA_DIR / "schema_sample.json"
CHANGELOG_FILE = DATA_DIR / "changelog_sample.json"


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_schema_summary() -> Dict[str, Any]:
    """
    Tool: Return a summary of tables and columns from schema_sample.json.
    """
    data = _load_json(SCHEMA_FILE)
    if data is None:
        return {
            "status": "error",
            "message": f"Schema file not found at {SCHEMA_FILE}",
        }
    return {
        "status": "success",
        "schema": data,
    }


def get_metric_lineage(metric_name: str) -> Dict[str, Any]:
    """
    Tool: Return tables/columns that feed a given metric,
    based on the 'metrics' section in schema_sample.json.
    """
    data = _load_json(SCHEMA_FILE)
    if data is None:
        return {
            "status": "error",
            "message": f"Schema file not found at {SCHEMA_FILE}",
        }

    metrics_info = data.get("metrics", {})
    metric_info = metrics_info.get(metric_name)
    if not metric_info:
        return {
            "status": "error",
            "message": f"No lineage info found for metric '{metric_name}'",
        }

    return {
        "status": "success",
        "metric": metric_name,
        "lineage": metric_info.get("depends_on", []),
    }


def get_recent_changes(
    since_date: Optional[str] = None,
    max_items: int = 20,
) -> Dict[str, Any]:
    """
    Tool: Return recent schema or pipeline changes from changelog_sample.json.
    """
    changes = _load_json(CHANGELOG_FILE) or []

    if since_date:
        changes = [c for c in changes if c.get("date", "") >= since_date]

    changes = sorted(changes, key=lambda c: c.get("date", ""), reverse=True)
    changes = changes[:max_items]

    return {
        "status": "success",
        "count": len(changes),
        "changes": changes,
    }
