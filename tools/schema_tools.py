from __future__ import annotations

from typing import Dict, Any, Optional
from pathlib import Path
import json

import pandas as pd

from .data_manager import get_data_source, get_sample_dir, is_using_sample, read_csv, detect_date_column, DataReadError


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _infer_schema_from_csv() -> Dict[str, Any]:
    """Auto-infer schema from the active CSV."""
    try:
        df = read_csv()
    except DataReadError as e:
        return {"status": "error", "message": str(e)}

    date_col = detect_date_column(df)
    columns = {}
    for col in df.columns:
        columns[col] = {
            "dtype": str(df[col].dtype),
            "null_count": int(df[col].isna().sum()),
            "total_rows": len(df),
            "role": "date" if col == date_col else "metric",
            "sample_values": [str(v) for v in df[col].head(3).tolist()],
        }
    return {
        "status": "success",
        "schema": {"columns": columns},
        "source": str(get_data_source()),
        "note": "Schema auto-inferred from CSV structure.",
    }


def _infer_lineage_from_csv(metric_name: str) -> Dict[str, Any]:
    """Auto-infer lineage from the active CSV when schema file has no entry."""
    try:
        df = read_csv()
    except DataReadError as e:
        return {"status": "error", "message": str(e)}

    if metric_name not in df.columns:
        return {
            "status": "error",
            "message": f"Metric '{metric_name}' not found in data source.",
        }
    col = df[metric_name]
    return {
        "status": "success",
        "metric": metric_name,
        "lineage": [],
        "inferred_schema": {
            "dtype": str(col.dtype),
            "null_count": int(col.isna().sum()),
            "sample_size": len(col),
        },
        "note": "Lineage auto-inferred from CSV (no schema file entry found).",
    }


def get_schema_summary() -> Dict[str, Any]:
    """
    Tool: Return a summary of tables and columns from schema_sample.json.
    """
    if is_using_sample():
        schema_path = get_sample_dir() / "schema_sample.json"
        data = _load_json(schema_path)
        if data is not None:
            return {"status": "success", "schema": data}
    return _infer_schema_from_csv()


def get_metric_lineage(metric_name: str) -> Dict[str, Any]:
    """
    Tool: Return tables/columns that feed a given metric,
    based on the 'metrics' section in schema_sample.json.
    """
    if is_using_sample():
        schema_path = get_sample_dir() / "schema_sample.json"
        data = _load_json(schema_path)
        if data is not None:
            metrics_info = data.get("metrics", {})
            metric_info = metrics_info.get(metric_name)
            if metric_info:
                return {
                    "status": "success",
                    "metric": metric_name,
                    "lineage": metric_info.get("depends_on", []),
                }
    return _infer_lineage_from_csv(metric_name)


def get_recent_changes(
    since_date: Optional[str] = None,
    max_items: int = 20,
) -> Dict[str, Any]:
    """
    Tool: Return recent schema or pipeline changes from changelog_sample.json.
    """
    if is_using_sample():
        changelog_path = get_sample_dir() / "changelog_sample.json"
        changes = _load_json(changelog_path) or []
    else:
        changes = []

    if since_date:
        changes = [c for c in changes if c.get("date", "") >= since_date]

    changes = sorted(changes, key=lambda c: c.get("date", ""), reverse=True)
    changes = changes[:max_items]

    return {
        "status": "success",
        "count": len(changes),
        "changes": changes,
    }
