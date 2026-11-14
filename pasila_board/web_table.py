"""Streamlit-taulun data ja riviväritys. Ei käynnistä Streamlit-palvelinta."""

from __future__ import annotations

import pandas as pd
from pandas.io.formats.style import Styler

from pasila_board.display import (
    MISSING_ESTIMATE,
    MISSING_TRACK,
    format_destination,
    format_estimate,
    format_scheduled,
)
from pasila_board.processing import Departure
from pasila_board.storage import DelayBucket

CANCELLED_STYLE = "background-color: #f8d7da; color: #721c24"
DELAYED_STYLE = "background-color: #fff3cd; color: #856404"


def departures_frame(departures: list[Departure]) -> pd.DataFrame:
    """Muunna lähdöt taulukoksi, jossa apusarakkeet väritystä varten."""
    rows = [
        {
            "Linja": item.line_id or "—",
            "Päämäärä": format_destination(item),
            "Lähtö": format_scheduled(item),
            "Ennuste": format_estimate(item),
            "Raide": item.track or MISSING_TRACK,
            "_cancelled": item.cancelled,
            "_delayed": item.is_delayed,
        }
        for item in departures
    ]
    return pd.DataFrame(rows)


VISIBLE_COLUMNS = ["Linja", "Päämäärä", "Lähtö", "Ennuste", "Raide"]


def style_departure_rows(frame: pd.DataFrame) -> Styler:
    """Korosta perutut (punainen) ja myöhässä olevat (keltainen)."""
    cancelled = frame["_cancelled"].to_numpy()
    delayed = frame["_delayed"].to_numpy()
    visible = frame[VISIBLE_COLUMNS]

    def row_styles(row: pd.Series) -> list[str]:
        index = int(row.name)
        if cancelled[index]:
            fill = CANCELLED_STYLE
        elif delayed[index]:
            fill = DELAYED_STYLE
        else:
            fill = ""
        return [fill] * len(row)

    return visible.style.apply(row_styles, axis=1).format(
        {column: str for column in VISIBLE_COLUMNS}
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
                    item.average_delay_minutes
                    if item.average_delay_minutes is not None
                    else MISSING_ESTIMATE
                ),
            }
            for item in buckets
        ]
    )
