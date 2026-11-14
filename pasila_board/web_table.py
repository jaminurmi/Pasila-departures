"""Streamlit-taulun data ja riviväritys. Ei käynnistä Streamlit-palvelinta."""

from __future__ import annotations

import html

import pandas as pd

from datetime import datetime

from pasila_board.display import (
    MISSING_ESTIMATE,
    MISSING_TRACK,
    format_destination,
    format_leave_home,
    format_scheduled,
)
from pasila_board.processing import (
    Departure,
    leave_home_deadline,
    missed_leave_home,
)
from pasila_board.storage import DelayBucket

CANCELLED_STYLE = "background-color: rgba(74, 16, 16, 0.25); color: #ff8a80"
DELAYED_STYLE = "background-color: rgba(107, 21, 21, 0.25); color: #ff6b6b"
MISSED_STYLE = "background-color: #e9ecef; color: #6c757d"
LEAVE_HOME_COLUMN = "Lähde viimeistään"


def departures_frame(
    departures: list[Departure],
    *,
    travel_seconds: int | None = None,
    buffer_minutes: int = 3,
    now: datetime | None = None,
) -> pd.DataFrame:
    """Muunna lähdöt taulukoksi, jossa apusarakkeet väritystä varten."""
    rows = []
    for item in departures:
        row: dict = {
            "Linja": item.line_id or "—",
            "Määränpää": format_destination(item),
            "Lähtö": format_scheduled(item),
            "Raide": item.track or MISSING_TRACK,
            "_cancelled": item.cancelled,
            "_delayed": item.is_delayed,
            "_missed": False,
        }
        if travel_seconds is not None and now is not None:
            deadline = leave_home_deadline(
                item,
                travel_seconds=travel_seconds,
                buffer_minutes=buffer_minutes,
            )
            missed = (not item.cancelled) and missed_leave_home(deadline, now)
            row[LEAVE_HOME_COLUMN] = format_leave_home(
                None if missed else deadline,
                cancelled=item.cancelled,
            )
            row["_missed"] = missed
        rows.append(row)
    return pd.DataFrame(rows)


VISIBLE_COLUMNS = ["Linja", "Määränpää", "Lähtö", "Raide"]
_ROW_LINE = "box-shadow: inset 0 -1px 0 rgba(255, 255, 255, 0.25);"
_HEADER_LINE = "box-shadow: inset 0 -1px 0 rgba(255, 255, 255, 0.7);"
_COLUMN_LAYOUT = {
    "Linja": "width:3.2rem;text-align:center;white-space:nowrap;",
    "Määränpää": "text-align:left;",
    "Lähtö": "width:7.2rem;text-align:center;white-space:nowrap;",
    "Raide": "width:3.4rem;text-align:center;white-space:nowrap;",
    LEAVE_HOME_COLUMN: "width:8.5rem;text-align:right;white-space:nowrap;",
}


def departures_table_html(frame: pd.DataFrame) -> str:
    """HTML-taulu, jossa vaakaviivat ovat solujen varjossa (Streamlit ei nollaa niitä)."""
    visible_names = _visible_column_names(frame)
    cancelled = frame["_cancelled"].to_list()
    delayed = frame["_delayed"].to_list()
    missed = (
        frame["_missed"].to_list()
        if "_missed" in frame.columns
        else [False] * len(frame)
    )
    header_cells = "".join(
        f'<th style="border:0;{_HEADER_LINE}padding:0.28rem 0.4rem;'
        f'font-weight:600;{_column_layout(name)}">'
        f"{html.escape(name)}</th>"
        for name in visible_names
    )
    body_rows = []
    for index, row in frame.iterrows():
        row_index = int(index)
        fill = _row_fill(cancelled[row_index], missed[row_index], delayed[row_index])
        cells = "".join(
            f'<td style="border:0;{_ROW_LINE}padding:0.28rem 0.4rem;'
            f'{_column_layout(name)}{fill}">'
            f"{html.escape(str(row[name]))}</td>"
            for name in visible_names
        )
        body_rows.append(f"<tr>{cells}</tr>")
    body = "".join(body_rows)
    return (
        '<table class="pasila-departures" style="width:100%;border-collapse:collapse;'
        'table-layout:fixed;border:0">'
        f"<thead><tr>{header_cells}</tr></thead>"
        f"<tbody>{body}</tbody>"
        "</table>"
    )


def _column_layout(name: str) -> str:
    return _COLUMN_LAYOUT.get(name, "text-align:left;")


def _visible_column_names(frame: pd.DataFrame) -> list[str]:
    names = list(VISIBLE_COLUMNS)
    if LEAVE_HOME_COLUMN in frame.columns:
        names.append(LEAVE_HOME_COLUMN)
    return names


def _row_fill(cancelled: bool, missed: bool, delayed: bool) -> str:
    if cancelled:
        return f"{CANCELLED_STYLE};"
    if missed:
        return f"{MISSED_STYLE};"
    if delayed:
        return f"{DELAYED_STYLE};"
    return ""


def stats_frame(buckets: list[DelayBucket], group_column: str) -> pd.DataFrame:
    """Tilastorivit Streamlit-taulukoksi."""
    return pd.DataFrame(
        [
            {
                group_column: item.label,
                "Havaintoja": item.sample_count,
                "Myöhässä": item.delayed_count,
                "Keskim. myöhästyminen (min)": (
                    f"{item.average_delay_minutes:.1f}"
                    if item.average_delay_minutes is not None
                    else MISSING_ESTIMATE
                ),
            }
            for item in buckets
        ]
    )
