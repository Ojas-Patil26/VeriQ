from __future__ import annotations

import math
from typing import Dict, Any, List, Optional

import pandas as pd

from .data_manager import read_csv, detect_date_column, DataReadError


def _to_numeric(series: pd.Series) -> Optional[pd.Series]:
    """Coerce a column to numeric; return None if it has no numeric values."""
    numeric = pd.to_numeric(series, errors="coerce")
    if len(numeric) > 0 and numeric.isna().all():
        return None
    return numeric


def list_metrics() -> Dict[str, Any]:
    """
    Tool: Return a list of available metric names from the metrics CSV.

    Only numeric columns qualify as metrics; text columns (e.g. region names)
    are excluded so downstream anomaly checks always have numbers to work with.
    """
    try:
        df = read_csv()
    except DataReadError as e:
        return {"status": "error", "message": str(e)}
    date_col = detect_date_column(df)
    metric_cols = [
        c for c in df.columns
        if c != date_col and _to_numeric(df[c]) is not None
    ]
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
    try:
        df = read_csv(parse_dates=True)
    except DataReadError as e:
        return {"status": "error", "message": str(e)}
    date_col = detect_date_column(df)

    if date_col is None:
        return {
            "status": "error",
            "message": "No date/time column detected in the CSV. Need a column named date, timestamp, time, or datetime.",
        }

    if metric_name not in df.columns:
        return {
            "status": "error",
            "message": f"Metric '{metric_name}' not found. Please call list_metrics first.",
        }

    df = df.sort_values(date_col)

    if start_date:
        try:
            df = df[df[date_col] >= pd.to_datetime(start_date)]
        except ValueError:
            return {"status": "error", "message": f"Invalid start_date: '{start_date}'"}
    if end_date:
        try:
            df = df[df[date_col] <= pd.to_datetime(end_date)]
        except ValueError:
            return {"status": "error", "message": f"Invalid end_date: '{end_date}'"}

    values = _to_numeric(df[metric_name])
    if values is None:
        return {
            "status": "error",
            "message": f"Metric '{metric_name}' is not numeric. Please call list_metrics to see valid metrics.",
        }

    points: List[Dict[str, Any]] = [
        {"date": d.date().isoformat(), "value": None if pd.isna(v) else float(v)}
        for d, v in zip(df[date_col], values)
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
    z_threshold: float = 2.0,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Tool: Simple anomaly detection using rolling z-scores.

    A point is flagged as an anomaly if:

        |z_score| >= z_threshold

    where z_score is computed against a rolling mean/std with the given window_size.
    Optionally filter to a date range with start_date / end_date (ISO format).
    """
    try:
        df = read_csv(parse_dates=True)
    except DataReadError as e:
        return {"status": "error", "message": str(e)}
    date_col = detect_date_column(df)

    if date_col is None:
        return {
            "status": "error",
            "message": "No date/time column detected in the CSV. Need a column named date, timestamp, time, or datetime.",
        }

    if metric_name not in df.columns:
        return {
            "status": "error",
            "message": f"Metric '{metric_name}' not found. Please call list_metrics first.",
        }

    df = df.sort_values(date_col)

    if start_date:
        try:
            df = df[df[date_col] >= pd.to_datetime(start_date)]
        except ValueError:
            return {"status": "error", "message": f"Invalid start_date: '{start_date}'"}
    if end_date:
        try:
            df = df[df[date_col] <= pd.to_datetime(end_date)]
        except ValueError:
            return {"status": "error", "message": f"Invalid end_date: '{end_date}'"}

    values = _to_numeric(df[metric_name])
    if values is None:
        return {
            "status": "error",
            "message": f"Metric '{metric_name}' is not numeric. Please call list_metrics to see valid metrics.",
        }

    df = df.copy()
    df["value"] = values

    # Time-based rolling window to handle date gaps correctly.
    # Shifted by 1 so the current point is excluded from its own window.
    df = df.set_index(date_col)
    rolling = df["value"].rolling(f"{window_size}D", min_periods=2)
    df["rolling_mean"] = rolling.mean().shift(1)
    df["rolling_std"] = rolling.std().shift(1)
    df = df.reset_index()

    # Replace zero std with NaN to avoid inf z-scores
    df["rolling_std"] = df["rolling_std"].replace(0, float("nan"))
    df["z_score"] = (df["value"] - df["rolling_mean"]) / df["rolling_std"]

    anomalies: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        z = row["z_score"]
        if pd.isna(z) or not math.isfinite(z):
            continue
        if abs(z) >= z_threshold:
            anomalies.append(
                {
                    "date": row[date_col].date().isoformat(),
                    "value": float(row["value"]),
                    "z_score": round(float(z), 4),
                    "direction": "high" if z > 0 else "low",
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
