"""Automated PDF data quality report.

Deterministic (no LLM call): renders the active dataset's health stats and a
per-metric time-series chart with anomaly markers into a downloadable PDF.
"""
from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any, Dict, List

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from fpdf import FPDF

from .tools.data_manager import (
    DataReadError,
    detect_date_column,
    get_data_source,
    is_using_sample,
    read_csv,
)
from .tools.metrics_tools import detect_metric_anomalies, list_metrics

# Chart ink tokens (light surface) — matches the dashboard's palette.
INK = (11, 11, 11)
SECONDARY = (82, 81, 78)
MUTED = (137, 135, 129)
FILL = (240, 239, 236)
SERIES_HEX = "#2a78d6"
ANOMALY_HEX = "#d03b3b"
GRID_HEX = "#e1e0d9"
BASELINE_HEX = "#c3c2b7"
MUTED_HEX = "#898781"

MAX_METRICS_IN_REPORT = 8
MAX_ANOMALY_ROWS = 12


def _latin(text: str) -> str:
    """FPDF core fonts are latin-1 only; degrade other characters gracefully."""
    return str(text).encode("latin-1", "replace").decode("latin-1")


def _metric_chart_png(dates: pd.Series, values: pd.Series, anomalies: List[Dict[str, Any]]) -> bytes:
    """Render one metric's time series with anomaly markers to PNG bytes."""
    fig, ax = plt.subplots(figsize=(7.2, 2.4), dpi=150)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    ax.plot(dates, values, color=SERIES_HEX, linewidth=2,
            solid_capstyle="round", solid_joinstyle="round", zorder=2)

    if anomalies:
        a_dates = pd.to_datetime([a["date"] for a in anomalies])
        a_values = [a["value"] for a in anomalies]
        # 2px white ring keeps markers legible where they sit on the line.
        ax.scatter(a_dates, a_values, s=46, color=ANOMALY_HEX,
                   edgecolors="white", linewidths=1.5, zorder=3, label="Anomaly")
        ax.legend(loc="upper left", frameon=False, fontsize=7,
                  labelcolor=MUTED_HEX, handletextpad=0.4)

    ax.grid(axis="y", color=GRID_HEX, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(BASELINE_HEX)
    ax.tick_params(colors=MUTED_HEX, labelsize=7, length=0)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:,.0f}" if abs(v) >= 1 else f"{v:g}")
    fig.tight_layout(pad=0.6)

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()


class _ReportPDF(FPDF):
    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", size=7)
        self.set_text_color(*MUTED)
        self.cell(0, 6, f"VeriQ automated data quality report  -  page {self.page_no()}/{{nb}}", align="C")


def _stat_row(pdf: _ReportPDF, stats: List[tuple[str, str]]) -> None:
    """A row of stat tiles: muted label over a bold value."""
    usable = pdf.w - pdf.l_margin - pdf.r_margin
    col_w = usable / len(stats)
    y = pdf.get_y()
    for i, (label, value) in enumerate(stats):
        x = pdf.l_margin + i * col_w
        pdf.set_xy(x, y)
        pdf.set_font("Helvetica", size=8)
        pdf.set_text_color(*MUTED)
        pdf.cell(col_w, 5, _latin(label))
        pdf.set_xy(x, y + 5)
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(*INK)
        pdf.cell(col_w, 7, _latin(value))
    pdf.set_y(y + 15)


def _anomaly_table(pdf: _ReportPDF, anomalies: List[Dict[str, Any]]) -> None:
    # Don't orphan the header row at the bottom of a page.
    if pdf.get_y() > pdf.h - 40:
        pdf.add_page()
    widths = (32, 40, 28, 24)
    headers = ("Date", "Value", "z-score", "Direction")
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*SECONDARY)
    pdf.set_fill_color(*FILL)
    for w, h in zip(widths, headers):
        pdf.cell(w, 6, h, fill=True)
    pdf.ln(6)
    pdf.set_font("Helvetica", size=8)
    pdf.set_text_color(*INK)
    for a in anomalies[:MAX_ANOMALY_ROWS]:
        pdf.cell(widths[0], 6, _latin(a["date"]))
        pdf.cell(widths[1], 6, f"{a['value']:,.2f}")
        pdf.cell(widths[2], 6, f"{a['z_score']:+.2f}")
        pdf.cell(widths[3], 6, a["direction"])
        pdf.ln(6)
    if len(anomalies) > MAX_ANOMALY_ROWS:
        pdf.set_text_color(*MUTED)
        pdf.cell(0, 6, f"... and {len(anomalies) - MAX_ANOMALY_ROWS} more")
        pdf.ln(6)


def build_pdf_report(window_size: int = 14, z_threshold: float = 2.0) -> bytes:
    """Build the full report for the active data source; raises DataReadError."""
    df = read_csv(parse_dates=True)
    date_col = detect_date_column(df)
    if date_col is None:
        raise DataReadError(
            "No date/time column detected in the CSV, so a time-series report "
            "cannot be generated."
        )
    df = df.sort_values(date_col)

    listing = list_metrics()
    if listing.get("status") != "success":
        raise DataReadError(listing.get("message", "Could not list metrics."))
    metric_names = listing["metrics"]
    if not metric_names:
        raise DataReadError("No numeric metric columns found in the data source.")

    source = get_data_source()
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    results: Dict[str, Dict[str, Any]] = {}
    for m in metric_names[:MAX_METRICS_IN_REPORT]:
        r = detect_metric_anomalies(m, window_size=window_size, z_threshold=z_threshold)
        if r.get("status") == "success":
            results[m] = r
    total_anomalies = sum(r["n_anomalies"] for r in results.values())

    date_gaps = df[date_col].drop_duplicates().sort_values().diff().dt.days
    max_gap = int(date_gaps.max()) if date_gaps.notna().any() else 0

    pdf = _ReportPDF(format="A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(16, 16, 16)
    pdf.add_page()

    # Title block
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*INK)
    pdf.cell(0, 10, "VeriQ Data Quality Report")
    pdf.ln(9)
    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(*SECONDARY)
    src_kind = "bundled sample data" if is_using_sample() else "uploaded file"
    pdf.cell(0, 6, _latin(f"Generated {generated}  -  Source: {source.name} ({src_kind})"))
    pdf.ln(5)
    pdf.cell(0, 6, _latin(
        f"Detector: rolling z-score, {window_size}-day window, flagged at |z| >= {z_threshold:g}"
    ))
    pdf.ln(10)

    # Overview stats
    date_range = f"{df[date_col].min().date().isoformat()} to {df[date_col].max().date().isoformat()}"
    _stat_row(pdf, [
        ("Rows", f"{len(df):,}"),
        ("Metrics", str(len(metric_names))),
        ("Anomalies", str(total_anomalies)),
        ("Largest date gap", f"{max_gap} day{'s' if max_gap != 1 else ''}"),
    ])
    pdf.set_font("Helvetica", size=8)
    pdf.set_text_color(*MUTED)
    pdf.cell(0, 5, _latin(f"Date range: {date_range}"))
    pdf.ln(10)

    # Per-metric sections
    for m, r in results.items():
        anomalies = r["anomalies"]
        # Keep each section's heading and chart together on one page.
        if pdf.get_y() > pdf.h - 95:
            pdf.add_page()

        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(*INK)
        pdf.cell(0, 8, _latin(m))
        pdf.ln(7)
        nulls = int(df[m].isna().sum()) if m in df.columns else 0
        pdf.set_font("Helvetica", size=8)
        pdf.set_text_color(*SECONDARY)
        status = (
            f"{len(anomalies)} anomal{'ies' if len(anomalies) != 1 else 'y'} flagged"
            if anomalies else "No anomalies flagged"
        )
        pdf.cell(0, 5, _latin(f"{status} at |z| >= {z_threshold:g}  -  {nulls} missing value(s)"))
        pdf.ln(7)

        values = pd.to_numeric(df[m], errors="coerce")
        png = _metric_chart_png(df[date_col], values, anomalies)
        pdf.image(io.BytesIO(png), w=pdf.w - pdf.l_margin - pdf.r_margin)
        pdf.ln(3)

        if anomalies:
            _anomaly_table(pdf, anomalies)
        pdf.ln(6)

    if len(metric_names) > MAX_METRICS_IN_REPORT:
        pdf.set_font("Helvetica", size=8)
        pdf.set_text_color(*MUTED)
        pdf.cell(0, 6, _latin(
            f"{len(metric_names) - MAX_METRICS_IN_REPORT} additional metric(s) omitted "
            f"(report covers the first {MAX_METRICS_IN_REPORT})."
        ))
        pdf.ln(8)

    # Column health appendix
    if pdf.get_y() > pdf.h - 60:
        pdf.add_page()
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*INK)
    pdf.cell(0, 8, "Column health")
    pdf.ln(8)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*SECONDARY)
    pdf.set_fill_color(*FILL)
    for w, h in zip((60, 40, 30), ("Column", "Type", "Nulls")):
        pdf.cell(w, 6, h, fill=True)
    pdf.ln(6)
    pdf.set_font("Helvetica", size=8)
    pdf.set_text_color(*INK)
    for col in df.columns:
        pdf.cell(60, 6, _latin(str(col)[:40]))
        pdf.cell(40, 6, str(df[col].dtype))
        pdf.cell(30, 6, f"{int(df[col].isna().sum()):,}")
        pdf.ln(6)

    return bytes(pdf.output())
