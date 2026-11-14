"""Haku + käsittely ilman käyttöliittymää."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from pasila_board.client import DigitrafficClient
from pasila_board.config import Settings
from pasila_board.processing import Departure, build_departures
from pasila_board.stations import StationDirectory
from pasila_board.storage import DepartureStore


@dataclass(frozen=True)
class DepartureBoard:
    """Valitun aseman näytettävä lähtölista."""

    station_code: str
    station_name: str
    departures: list[Departure]


def load_departure_board(
    client: DigitrafficClient,
    stations: StationDirectory,
    settings: Settings,
    station_code: str,
    store: DepartureStore | None = None,
    via_station_code: str | None = None,
) -> DepartureBoard:
    """Hae junat, tallenna ne tarvittaessa ja palauta lähtötaulu."""
    now = datetime.now(ZoneInfo(settings.timezone_name))
    fetch_count = settings.departing_trains
    departures: list[Departure] = []
    while True:
        trains = client.fetch_departing_trains(
            station_code,
            departing_trains=fetch_count,
        )
        departures = build_departures(
            trains,
            station_code=station_code,
            name_for=stations.name_for,
            timezone_name=settings.timezone_name,
            now=now,
            limit=settings.display_limit,
            hub_codes=settings.destination_hub_codes,
            via_station_code=via_station_code,
        )
        if via_station_code is None:
            break
        if len(departures) >= settings.display_limit:
            break
        if fetch_count >= settings.max_departing_trains:
            break
        if len(trains) < fetch_count:
            break
        fetch_count = min(
            fetch_count + settings.departing_trains,
            settings.max_departing_trains,
        )
    if store is not None:
        store.upsert_departures(station_code, departures, recorded_at=now)
    return DepartureBoard(
        station_code=station_code,
        station_name=stations.name_for(station_code),
        departures=departures,
    )
