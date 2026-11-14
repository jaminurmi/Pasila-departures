"""SQLite-avaimen ja tilastojen testit ilman HTTP-kutsuja."""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from pasila_board.processing import Departure
from pasila_board.storage import DepartureStore

HELSINKI = ZoneInfo("Europe/Helsinki")


def _departure(**overrides: object) -> Departure:
    values: dict = {
        "train_number": 8200,
        "departure_date": "2026-11-14",
        "line_id": "A",
        "destination_code": "HKI",
        "destination_name": "Helsinki asema",
        "scheduled_local": datetime(2026, 11, 14, 14, 28, tzinfo=HELSINKI),
        "estimate_local": None,
        "track": "10",
        "cancelled": False,
        "delay_minutes": 0,
        "unknown_delay": False,
    }
    values.update(overrides)
    return Departure(**values)


def test_unique_key_updates_same_train_station_date(tmp_path: Path) -> None:
    store = DepartureStore(tmp_path / "board.sqlite")
    first = _departure(delay_minutes=0)
    later = _departure(
        delay_minutes=4,
        estimate_local=datetime(2026, 11, 14, 14, 32, tzinfo=HELSINKI),
    )
    recorded = datetime(2026, 11, 14, 14, 20, tzinfo=HELSINKI)
    store.upsert_departures("PSL", [first], recorded_at=recorded)
    store.upsert_departures("PSL", [later], recorded_at=recorded)

    by_line = store.delay_stats_by_line("PSL")
    assert len(by_line) == 1
    assert by_line[0].sample_count == 1
    assert by_line[0].delayed_count == 1
    assert by_line[0].average_delay_minutes == 4.0


def test_stats_group_by_line_and_hour(tmp_path: Path) -> None:
    store = DepartureStore(tmp_path / "board.sqlite")
    recorded = datetime(2026, 11, 14, 15, 0, tzinfo=HELSINKI)
    store.upsert_departures(
        "PSL",
        [
            _departure(train_number=1, line_id="A", delay_minutes=2),
            _departure(
                train_number=2,
                line_id="K",
                delay_minutes=0,
                scheduled_local=datetime(2026, 11, 14, 8, 5, tzinfo=HELSINKI),
            ),
            _departure(
                train_number=3,
                line_id="A",
                delay_minutes=6,
                scheduled_local=datetime(2026, 11, 14, 14, 40, tzinfo=HELSINKI),
            ),
        ],
        recorded_at=recorded,
    )

    by_line = {item.label: item for item in store.delay_stats_by_line("PSL")}
    assert by_line["A"].sample_count == 2
    assert by_line["A"].delayed_count == 2
    assert by_line["A"].average_delay_minutes == 4.0
    assert by_line["K"].delayed_count == 0

    by_hour = {item.label: item for item in store.delay_stats_by_hour("PSL")}
    assert by_hour["14:00–14:59"].sample_count == 2
    assert by_hour["08:00–08:59"].sample_count == 1


def test_cancelled_trains_are_excluded_from_delay_stats(tmp_path: Path) -> None:
    store = DepartureStore(tmp_path / "board.sqlite")
    recorded = datetime(2026, 11, 14, 15, 0, tzinfo=HELSINKI)
    store.upsert_departures(
        "PSL",
        [
            _departure(train_number=9, cancelled=True, delay_minutes=20),
            _departure(train_number=10, delay_minutes=3),
        ],
        recorded_at=recorded,
    )
    by_line = store.delay_stats_by_line("PSL")
    assert len(by_line) == 1
    assert by_line[0].sample_count == 1
    assert by_line[0].average_delay_minutes == 3.0
