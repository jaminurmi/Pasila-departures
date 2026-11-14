"""Asemanimien haku ja prosessikohtainen välimuisti."""

from __future__ import annotations

from typing import Any, Mapping

from pasila_board.client import DigitrafficClient


class StationDirectory:
    """Muuntaa asemakoodin (esim. HKI) nimeksi. Nimet haetaan kerran."""

    def __init__(
        self,
        client: DigitrafficClient,
        display_names: Mapping[str, str] | None = None,
    ) -> None:
        self._client = client
        self._display_names = dict(display_names or {})
        self._names: dict[str, str] | None = None

    def name_for(self, station_code: str) -> str:
        """Palauta aseman nimi tai koodi, jos nimeä ei löydy."""
        override = self._display_names.get(station_code)
        if override:
            return override
        return self._name_index().get(station_code, station_code)

    def _name_index(self) -> dict[str, str]:
        if self._names is None:
            self._names = _index_station_names(self._client.fetch_stations())
        return self._names


def _index_station_names(rows: list[dict[str, Any]]) -> dict[str, str]:
    """Rakenna koodi → nimi -sanakirja metadata-vastauksesta."""
    names: dict[str, str] = {}
    for row in rows:
        code = row.get("stationShortCode")
        name = row.get("stationName")
        if isinstance(code, str) and isinstance(name, str) and code:
            names[code] = name
    return names
