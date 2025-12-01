from __future__ import annotations

from typing import Dict, Any, List, Optional
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
METRICS_FILE = DATA_DIR / "metrics_sample.csv"


def list_metrics() -> Dict[str, Any]:
    """
    Tool: Return a list of available metric names from the metrics CSV.
    """
    df = pd.read_csv(METRICS_FILE)
    metric_cols = [c for c in df.columns if c != "date"]
    return {
        "status": "success",
        "metrics": metric_cols,
        "count": len(metric_cols),
    }


def get_metric_timeseries(
    metric_name: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Tool: Return the time series for a given metric as a list of {date, value}.
    """
    df = pd.read_csv(METRICS_FILE, parse_dates=["date"])

    if metric_name not in df.columns:
        return {
            "status": "error",
            "message": f"Metric '{metric_name}' not found. Please call list_metrics first.",
        }

    if start_date:
        df = df[df["date"] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df["date"] <= pd.to_datetime(end_date)]

    points: List[Dict[str, Any]] = [
        {"date": d.date().isoformat(), "value": float(v)}
        for d, v in zip(df["date"], df[metric_name])
    ]

    return {
        "status": "success",
        "metric": metric_name,
        "points": points,
        "n_points": len(points),
    }


def detect_metric_anomalies(
    metric_name: str,
    window_size: int = 14,
    z_threshold: float = 3.0,
) -> Dict[str, Any]:
    """
    Tool: Simple anomaly detection using rolling z-scores.
    """
    df = pd.read_csv(METRICS_FILE, parse_dates=["date"])

    if metric_name not in df.columns:
        return {
            "status": "error",
            "message": f"Metric '{metric_name}' not found. Please call list_metrics first.",
        }

    df = df.sort_values("date")
    df["value"] = df[metric_name].astype(float)

    df["rolling_mean"] = df["value"].rolling(window=window_size).mean()
    df["rolling_std"] = df["value"].rolling(window=window_size).std()

    df["z_score"] = (df["value"] - df["rolling_mean"]) / df["rolling_std"]

    anomalies: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        if pd.isna(row["z_score"]):
            continue
        if abs(row["z_score"]) >= z_threshold:
            anomalies.append(
                {
                    "date": row["date"].date().isoformat(),
                    "value": float(row["value"]),
                    "z_score": float(row["z_score"]),
                    "direction": "high" if row["z_score"] > 0 else "low",
                }
            )

    return {
        "status": "success",
        "metric": metric_name,
        "window_size": window_size,
        "z_threshold": z_threshold,
        "n_anomalies": len(anomalies),
        "anomalies": anomalies,
    }
