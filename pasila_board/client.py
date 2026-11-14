"""Digitraffic Rail API -kutsut. Ei sisällä näytön tai suodatuksen logiikkaa."""

from __future__ import annotations

from typing import Any

import requests

from pasila_board.config import Settings


class DigitrafficError(Exception):
    """Rajapintakutsu epäonnistui tai vastaus oli käyttökelvoton."""


class DigitrafficClient:
    """Hakee junat ja asemetiedot HTTP:llä.

    Jokaisessa pyynnössä lähetetään Digitraffic-User-otsikko.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Digitraffic-User": settings.digitraffic_user,
                "Accept": "application/json",
                # Ilman gzip-neuvottelua rajapinta vastaa HTTP 406.
                "Accept-Encoding": "gzip",
            }
        )

    def fetch_stations(self) -> list[dict[str, Any]]:
        """Palauta /metadata/stations -listaus."""
        return self._get_json("/metadata/stations")

    def fetch_departing_trains(self, station_code: str) -> list[dict[str, Any]]:
        """Palauta aseman seuraavat lähtevät lähijunat (raaka JSON)."""
        params = {
            "arrived_trains": 0,
            "arriving_trains": 0,
            "departed_trains": 0,
            "departing_trains": self._settings.departing_trains,
            "include_nonstopping": "false",
            "train_categories": self._settings.train_categories,
        }
        path = f"/live-trains/station/{station_code}"
        return self._get_json(path, params=params)

    def _get_json(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        url = f"{self._settings.base_url}{path}"
        try:
            response = self._session.get(
                url,
                params=params,
                timeout=self._settings.request_timeout_seconds,
            )
        except requests.Timeout as exc:
            raise DigitrafficError(
                "Digitraffic ei vastannut ajoissa (timeout)."
            ) from exc
        except requests.RequestException as exc:
            raise DigitrafficError(
                f"Digitraffic-kutsu epäonnistui: {exc}"
            ) from exc

        if not response.ok:
            raise DigitrafficError(
                f"Digitraffic palautti HTTP {response.status_code}."
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise DigitrafficError(
                "Digitrafficin vastaus ei ollut kelvollista JSONia."
            ) from exc

        if not isinstance(payload, list):
            raise DigitrafficError(
                "Digitrafficin vastauksen juuri ei ollut lista."
            )
        # Tyhjä lista on rajapinnalle kelvollinen vastaus (ei junia).
        return payload
