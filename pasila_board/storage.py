"""SQLite-tallennus ja myöhästymistilastot. Ei HTTP-kutsuja."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pasila_board.processing import Departure

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS departures (
    train_number INTEGER NOT NULL,
    departure_date TEXT NOT NULL,
    station_code TEXT NOT NULL,
    line_id TEXT NOT NULL,
    hour_local INTEGER NOT NULL,
    delay_minutes INTEGER,
    cancelled INTEGER NOT NULL,
    delayed INTEGER NOT NULL,
    recorded_at TEXT NOT NULL,
    PRIMARY KEY (train_number, departure_date, station_code)
)
"""

_UPSERT = """
INSERT INTO departures (
    train_number, departure_date, station_code,
    line_id, hour_local, delay_minutes, cancelled, delayed, recorded_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(train_number, departure_date, station_code) DO UPDATE SET
    line_id = excluded.line_id,
    hour_local = excluded.hour_local,
    delay_minutes = excluded.delay_minutes,
    cancelled = excluded.cancelled,
    delayed = excluded.delayed,
    recorded_at = excluded.recorded_at
"""

_STATS_BY_LINE = """
SELECT line_id, COUNT(*), SUM(delayed), AVG(delay_minutes)
FROM departures
WHERE station_code = ? AND cancelled = 0
GROUP BY line_id
ORDER BY line_id
"""

_STATS_BY_HOUR = """
SELECT hour_local, COUNT(*), SUM(delayed), AVG(delay_minutes)
FROM departures
WHERE station_code = ? AND cancelled = 0
GROUP BY hour_local
ORDER BY hour_local
"""


@dataclass(frozen=True)
class DelayBucket:
    """Yhden linjan tai kellonajan myöhästymiset."""

    label: str
    sample_count: int
    delayed_count: int
    average_delay_minutes: float | None


class DepartureStore:
    """Tallentaa lähdöt SQLiteen ja laskee tilastot."""

    def __init__(self, database_path: Path) -> None:
        self._path = database_path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(_CREATE_TABLE)

    def upsert_departures(
        self,
        station_code: str,
        departures: list[Departure],
        *,
        recorded_at: datetime,
    ) -> None:
        """Lisää tai päivitä lähdöt. Avain: junanumero + lähtöpäivä + asema."""
        recorded = recorded_at.isoformat()
        rows = [
            (
                item.train_number,
                item.departure_date,
                station_code,
                item.line_id,
                item.scheduled_local.hour,
                item.delay_minutes,
                int(item.cancelled),
                int(item.is_delayed),
                recorded,
            )
            for item in departures
        ]
        with self._connect() as connection:
            connection.executemany(_UPSERT, rows)

    def delay_stats_by_line(self, station_code: str) -> list[DelayBucket]:
        """Myöhästymiset linjoittain, perutut jätetään pois."""
        return self._query_buckets(
            _STATS_BY_LINE,
            station_code,
            label_format=lambda value: str(value),
        )

    def delay_stats_by_hour(self, station_code: str) -> list[DelayBucket]:
        """Myöhästymiset kellonajoittain (Europe/Helsinki-tunti)."""
        return self._query_buckets(
            _STATS_BY_HOUR,
            station_code,
            label_format=lambda hour: f"{int(hour):02d}:00–{int(hour):02d}:59",
        )

    def _query_buckets(
        self,
        sql: str,
        station_code: str,
        *,
        label_format: Callable[[object], str],
    ) -> list[DelayBucket]:
        with self._connect() as connection:
            fetched = connection.execute(sql, (station_code,)).fetchall()
        buckets: list[DelayBucket] = []
        for label, sample_count, delayed_count, average in fetched:
            buckets.append(
                DelayBucket(
                    label=label_format(label),
                    sample_count=int(sample_count),
                    delayed_count=int(delayed_count or 0),
                    average_delay_minutes=(
                        round(float(average), 1) if average is not None else None
                    ),
                )
            )
        return buckets

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
