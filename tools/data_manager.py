from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

_SAMPLE_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_SAMPLE_CSV = _SAMPLE_DATA_DIR / "metrics_sample.csv"

_active_csv: Optional[Path] = None


def set_data_source(path: Path) -> None:
    """Point all tools at a user-uploaded CSV."""
    global _active_csv
    _active_csv = Path(path)


def get_data_source() -> Path:
    """Return the active CSV path (user-uploaded or sample fallback)."""
    return _active_csv or _SAMPLE_CSV


def reset_to_sample() -> None:
    """Reset to the bundled sample data."""
    global _active_csv
    _active_csv = None


def is_using_sample() -> bool:
    """True when no custom CSV has been set (using bundled sample data)."""
    return _active_csv is None


def get_sample_dir() -> Path:
    """Return the path to the bundled data/ directory."""
    return _SAMPLE_DATA_DIR


# -- Shared helpers used by metrics_tools and schema_tools --

def detect_date_column(df: pd.DataFrame) -> Optional[str]:
    """Find the datetime column by name convention or dtype."""
    for col in df.columns:
        if col.lower() in ("date", "timestamp", "time", "datetime", "dt"):
            return col
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            return col
    return None


class DataReadError(Exception):
    """Raised when the active CSV cannot be read."""
    pass


def read_csv(parse_dates: bool = False) -> pd.DataFrame:
    """Read the active CSV into a DataFrame.

    Raises DataReadError with a human-friendly message on failure.
    """
    path = get_data_source()
    if not path.exists():
        raise DataReadError(f"Metrics CSV not found at {path}")
    try:
        df = pd.read_csv(path)
    except Exception as e:
        raise DataReadError(f"Could not parse metrics CSV: {e}") from e
    if parse_dates:
        date_col = detect_date_column(df)
        if date_col is not None:
            parsed = pd.to_datetime(df[date_col], errors="coerce")
            if len(df) > 0 and parsed.isna().all():
                raise DataReadError(
                    f"Column '{date_col}' looks like a date column but none of "
                    "its values could be parsed as dates."
                )
            # Drop rows whose date is unparseable — they can't be placed on a timeline.
            df[date_col] = parsed
            df = df[parsed.notna()].reset_index(drop=True)
    return df
