"""Konsolisovelluksen käynnistys: haku → käsittely → tulostus."""

from __future__ import annotations

import sys

from pasila_board.board import load_departure_board
from pasila_board.client import DigitrafficClient, DigitrafficError
from pasila_board.config import SETTINGS
from pasila_board.console import render_departures
from pasila_board.stations import StationDirectory
from pasila_board.storage import DepartureStore


def main() -> int:
    settings = SETTINGS
    client = DigitrafficClient(settings)
    stations = StationDirectory(client, settings.station_display_names)
    store = DepartureStore(settings.database_path)

    try:
        board = load_departure_board(
            client,
            stations,
            settings,
            settings.station_code,
            store,
        )
    except DigitrafficError as exc:
        print(exc, file=sys.stderr)
        return 1

    render_departures(
        board.departures,
        station_name=board.station_name,
        attribution=settings.source_attribution,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
