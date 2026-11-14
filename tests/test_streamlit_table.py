"""Streamlit-taulun rivivärityksen testit ilman palvelinta."""

from datetime import datetime
from zoneinfo import ZoneInfo

from pasila_board.processing import Departure
from pasila_board.web_table import departures_frame, departures_table_html

HELSINKI = ZoneInfo("Europe/Helsinki")


def test_cancelled_and_delayed_rows_use_red_background() -> None:
    cancelled = _departure(cancelled=True)
    delayed = _departure(
        estimate_local=datetime(2026, 11, 9, 20, 40, tzinfo=HELSINKI),
        delay_minutes=2,
    )
    html = departures_table_html(departures_frame([cancelled, delayed]))
    assert "Linja" in html
    assert "Määränpää" in html
    assert "text-align:center" in html
    assert "Lähtö" in html
    assert "Raide" in html
    assert "rgba(107, 21, 21, 0.25)" in html
    assert "rgba(74, 16, 16, 0.25)" in html
    assert "#fff3cd" not in html
    assert "peruttu" in html
    assert "20:38 +2" in html
    assert "Ennuste" not in html
    assert "_cancelled" not in html
    assert "box-shadow: inset 0 -1px 0" in html


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
