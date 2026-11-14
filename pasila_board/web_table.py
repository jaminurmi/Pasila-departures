"""Streamlit-taulun data ja riviväritys. Ei käynnistä Streamlit-palvelinta."""

from __future__ import annotations

import pandas as pd
from pandas.io.formats.style import Styler

from datetime import datetime

from pasila_board.display import (
    MISSING_ESTIMATE,
    MISSING_TRACK,
    format_destination,
    format_estimate,
    format_leave_home,
    format_scheduled,
)
from pasila_board.processing import (
    Departure,
    leave_home_deadline,
    missed_leave_home,
)
from pasila_board.storage import DelayBucket

CANCELLED_STYLE = "background-color: #f8d7da; color: #721c24"
DELAYED_STYLE = "background-color: #f8d7da; color: #721c24"
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
            "Päämäärä": format_destination(item),
            "Lähtö": format_scheduled(item),
            "Ennuste": format_estimate(item),
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


VISIBLE_COLUMNS = ["Linja", "Päämäärä", "Lähtö", "Ennuste", "Raide"]


def style_departure_rows(frame: pd.DataFrame) -> Styler:
    """Korosta perutut ja myöhässä punaisina, myöhästyneet kotoa harmaana."""
    cancelled = frame["_cancelled"].to_numpy()
    delayed = frame["_delayed"].to_numpy()
    missed = (
        frame["_missed"].to_numpy()
        if "_missed" in frame.columns
        else [False] * len(frame)
    )
    visible_names = list(VISIBLE_COLUMNS)
    if LEAVE_HOME_COLUMN in frame.columns:
        visible_names.append(LEAVE_HOME_COLUMN)
    visible = frame[visible_names]

    def row_styles(row: pd.Series) -> list[str]:
        index = int(row.name)
        if cancelled[index]:
            fill = CANCELLED_STYLE
        elif missed[index]:
            fill = MISSED_STYLE
        elif delayed[index]:
            fill = DELAYED_STYLE
        else:
            fill = ""
        return [fill] * len(row)

    return visible.style.apply(row_styles, axis=1).format(
        {column: str for column in visible_names}
    )


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
