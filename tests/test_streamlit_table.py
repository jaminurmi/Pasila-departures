"""Streamlit-taulun rivivärityksen testit ilman palvelinta."""

from datetime import datetime
from zoneinfo import ZoneInfo

from pasila_board.processing import Departure
from pasila_board.web_table import departures_frame, style_departure_rows

HELSINKI = ZoneInfo("Europe/Helsinki")


def test_cancelled_and_delayed_rows_get_distinct_colors() -> None:
    cancelled = _departure(cancelled=True)
    delayed = _departure(
        estimate_local=datetime(2026, 11, 9, 20, 40, tzinfo=HELSINKI),
        delay_minutes=2,
    )
    styled = style_departure_rows(departures_frame([cancelled, delayed]))
    html = styled.to_html()
    assert list(styled.data.columns) == [
        "Linja",
        "Päämäärä",
        "Lähtö",
        "Ennuste",
        "Raide",
    ]
    assert "#f8d7da" in html
    assert "#fff3cd" in html
    assert "peruttu" in html
    assert "+2 min" in html
    assert "_cancelled" not in html


def _departure(**overrides: object) -> Departure:
    values: dict = {
        "train_number": 8200,
        "departure_date": "2026-11-09",
        "line_id": "A",
        "destination_code": "HKI",
        "destination_name": "Helsinki asema",
        "scheduled_local": datetime(2026, 11, 9, 20, 38, tzinfo=HELSINKI),
        "estimate_local": None,
        "track": None,
        "cancelled": False,
        "delay_minutes": None,
        "unknown_delay": False,
    }
    values.update(overrides)
    return Departure(**values)
