"""Kotoa-lähdön laskennan testit ilman verkkoa."""

from datetime import datetime
from zoneinfo import ZoneInfo

from pasila_board.display import LEAVE_HOME_MISSED, format_leave_home
from pasila_board.processing import Departure, leave_home_deadline, missed_leave_home
from pasila_board.web_table import LEAVE_HOME_COLUMN, departures_frame, departures_table_html

HELSINKI = ZoneInfo("Europe/Helsinki")


def _departure(**overrides: object) -> Departure:
    values: dict = {
        "train_number": 8200,
        "departure_date": "2026-11-14",
        "line_id": "A",
        "destination_code": "HKI",
        "destination_name": "Päärautatieasema",
        "scheduled_local": datetime(2026, 11, 14, 14, 30, tzinfo=HELSINKI),
        "estimate_local": None,
        "track": "10",
        "cancelled": False,
        "delay_minutes": None,
        "unknown_delay": False,
    }
    values.update(overrides)
    return Departure(**values)


def test_leave_home_uses_estimate_when_available() -> None:
    item = _departure(
        estimate_local=datetime(2026, 11, 14, 14, 35, tzinfo=HELSINKI),
        delay_minutes=5,
    )
    deadline = leave_home_deadline(item, travel_seconds=10 * 60, buffer_minutes=3)
    assert deadline == datetime(2026, 11, 14, 14, 22, tzinfo=HELSINKI)


def test_leave_home_uses_schedule_without_estimate() -> None:
    item = _departure()
    deadline = leave_home_deadline(item, travel_seconds=8 * 60, buffer_minutes=3)
    assert deadline == datetime(2026, 11, 14, 14, 19, tzinfo=HELSINKI)


def test_missed_leave_home_when_deadline_has_passed() -> None:
    deadline = datetime(2026, 11, 14, 14, 10, tzinfo=HELSINKI)
    now = datetime(2026, 11, 14, 14, 11, tzinfo=HELSINKI)
    assert missed_leave_home(deadline, now) is True
    assert format_leave_home(None, cancelled=False) == LEAVE_HOME_MISSED


def test_leave_home_column_hidden_without_travel_time() -> None:
    frame = departures_frame([_departure()])
    html = departures_table_html(frame)
    assert LEAVE_HOME_COLUMN not in frame.columns
    assert LEAVE_HOME_COLUMN not in html


def test_missed_row_is_gray_in_table() -> None:
    now = datetime(2026, 11, 14, 14, 25, tzinfo=HELSINKI)
    item = _departure()
    html = departures_table_html(
        departures_frame(
            [item],
            travel_seconds=20 * 60,
            buffer_minutes=3,
            now=now,
        )
    )
    assert LEAVE_HOME_COLUMN in html
    assert "ei ehdi" in html
    assert "#e9ecef" in html
