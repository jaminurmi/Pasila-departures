"""SQLite-tallennus ja myöhästymistilastot. Ei HTTP-kutsuja."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pasila_board.processing import Departure
from pasila_board.travel import Coordinates

_CREATE_PROFILE = """
CREATE TABLE IF NOT EXISTS user_profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    given_name TEXT NOT NULL DEFAULT '',
    family_name TEXT NOT NULL DEFAULT '',
    address TEXT NOT NULL DEFAULT '',
    direction_code TEXT NOT NULL DEFAULT 'HKI'
)
"""

_CREATE_GEOCODE = """
CREATE TABLE IF NOT EXISTS geocode_cache (
    address_key TEXT PRIMARY KEY,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL
)
"""

_CREATE_TRAVEL = """
CREATE TABLE IF NOT EXISTS travel_cache (
    address_key TEXT NOT NULL,
    travel_mode TEXT NOT NULL,
    duration_seconds INTEGER NOT NULL,
    PRIMARY KEY (address_key, travel_mode)
)
"""

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
class UserProfile:
    """Paikallisesti tallennettu käyttäjä. Nimeä ei lähetetä ulos."""

    given_name: str = ""
    family_name: str = ""
    address: str = ""
    direction_code: str = "HKI"


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
            connection.execute(_CREATE_PROFILE)
            connection.execute(_CREATE_GEOCODE)
            connection.execute(_CREATE_TRAVEL)

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

    def load_profile(self) -> UserProfile:
        """Palauta tallennettu profiili tai tyhjät oletukset."""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT given_name, family_name, address, direction_code
                FROM user_profile WHERE id = 1
                """
            ).fetchone()
        if row is None:
            return UserProfile()
        return UserProfile(
            given_name=row[0],
            family_name=row[1],
            address=row[2],
            direction_code=row[3] or "HKI",
        )

    def save_profile(self, profile: UserProfile) -> None:
        """Tallenna profiili paikallisesti. Ei verkkokutsuja."""
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO user_profile (
                    id, given_name, family_name, address, direction_code
                ) VALUES (1, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    given_name = excluded.given_name,
                    family_name = excluded.family_name,
                    address = excluded.address,
                    direction_code = excluded.direction_code
                """,
                (
                    profile.given_name.strip(),
                    profile.family_name.strip(),
                    profile.address.strip(),
                    profile.direction_code,
                ),
            )

    def cached_coordinates(self, address: str) -> Coordinates | None:
        """Palauta välimuistissa oleva geokoodaus tai None."""
        key = _address_key(address)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT latitude, longitude FROM geocode_cache WHERE address_key = ?",
                (key,),
            ).fetchone()
        if row is None:
            return None
        return Coordinates(latitude=row[0], longitude=row[1])

    def save_coordinates(self, address: str, coords: Coordinates) -> None:
        """Tallenna geokoodaus paikallisesti."""
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO geocode_cache (address_key, latitude, longitude)
                VALUES (?, ?, ?)
                ON CONFLICT(address_key) DO UPDATE SET
                    latitude = excluded.latitude,
                    longitude = excluded.longitude
                """,
                (_address_key(address), coords.latitude, coords.longitude),
            )

    def cached_travel_seconds(self, address: str, travel_mode: str) -> int | None:
        """Palauta välimuistissa oleva matka-aika tai None."""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT duration_seconds FROM travel_cache
                WHERE address_key = ? AND travel_mode = ?
                """,
                (_address_key(address), travel_mode),
            ).fetchone()
        if row is None:
            return None
        return int(row[0])

    def save_travel_seconds(
        self,
        address: str,
        travel_mode: str,
        duration_seconds: int,
    ) -> None:
        """Tallenna matka-aika paikallisesti."""
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO travel_cache (address_key, travel_mode, duration_seconds)
                VALUES (?, ?, ?)
                ON CONFLICT(address_key, travel_mode) DO UPDATE SET
                    duration_seconds = excluded.duration_seconds
                """,
                (_address_key(address), travel_mode, duration_seconds),
            )

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


def _address_key(address: str) -> str:
    return " ".join(address.casefold().split())
