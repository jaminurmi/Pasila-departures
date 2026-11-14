"""Digitransit-geokoodaus ja reititys. Nimeä ei lähetetä."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests

from pasila_board.config import Settings


class TravelError(Exception):
    """Osoitetta ei löydy, reititys epäonnistui tai avain puuttuu."""


@dataclass(frozen=True)
class Coordinates:
    """WGS 84 -piste."""

    latitude: float
    longitude: float


_WALK_MODE = "walk"


def _plan_query(origin: Coordinates, destination: Coordinates) -> str:
    """Rakenna planConnection-kysely. Koordinaatit ovat lukuja, ei merkkijonoja."""
    modes_arg = "    modes: {direct: [WALK], directOnly: true}\n"
    return f"""
{{
  planConnection(
    origin: {{location: {{coordinate: {{latitude: {origin.latitude}, longitude: {origin.longitude}}}}}}}
    destination: {{location: {{coordinate: {{latitude: {destination.latitude}, longitude: {destination.longitude}}}}}}}
{modes_arg}    first: 1
  ) {{
    edges {{
      node {{
        start
        end
        legs {{
          duration
        }}
      }}
    }}
  }}
}}
"""


class DigitransitClient:
    """Hakee koordinaatit ja matka-ajan. Vain osoite lähtee rajapintaan."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._session = requests.Session()

    def geocode_address(self, address: str) -> Coordinates:
        """Muunna osoite koordinaateiksi. Tyhjä tulos on virhe."""
        payload = self._get_json(
            self._settings.digitransit_geocode_url,
            params={
                "text": address,
                "size": 1,
                "lang": "fi",
                "focus.point.lat": self._settings.pasila_latitude,
                "focus.point.lon": self._settings.pasila_longitude,
            },
        )
        return parse_geocode_response(payload)

    def travel_seconds(self, origin: Coordinates) -> int:
        """Kävelyaika Pasilaan sekunteina."""
        destination = Coordinates(
            latitude=self._settings.pasila_latitude,
            longitude=self._settings.pasila_longitude,
        )
        body = {"query": _plan_query(origin, destination)}
        payload = self._post_json(self._settings.digitransit_routing_url, body)
        return parse_plan_duration(payload)

    def _headers(self) -> dict[str, str]:
        key = self._settings.digitransit_subscription_key
        if not key:
            raise TravelError(
                "Digitransit-avain puuttuu. Aseta DIGITRANSIT_SUBSCRIPTION_KEY "
                "tiedostoon .env (ks. .env.example)."
            )
        return {
            "digitransit-subscription-key": key,
            "Accept": "application/json",
        }

    def _get_json(self, url: str, params: dict[str, Any]) -> Any:
        try:
            response = self._session.get(
                url,
                params=params,
                headers=self._headers(),
                timeout=self._settings.request_timeout_seconds,
            )
        except requests.Timeout as exc:
            raise TravelError("Digitransit ei vastannut ajoissa (timeout).") from exc
        except requests.RequestException as exc:
            raise TravelError(f"Digitransit-kutsu epäonnistui: {exc}") from exc
        return self._read_json(response)

    def _post_json(self, url: str, body: dict[str, Any]) -> Any:
        headers = self._headers()
        headers["Content-Type"] = "application/json"
        try:
            response = self._session.post(
                url,
                json=body,
                headers=headers,
                timeout=self._settings.request_timeout_seconds,
            )
        except requests.Timeout as exc:
            raise TravelError("Digitransit ei vastannut ajoissa (timeout).") from exc
        except requests.RequestException as exc:
            raise TravelError(f"Digitransit-kutsu epäonnistui: {exc}") from exc
        return self._read_json(response)

    def _read_json(self, response: requests.Response) -> Any:
        if response.status_code in {401, 403}:
            raise TravelError("Digitransit hylkäsi API-avaimen.")
        if not response.ok:
            raise TravelError(f"Digitransit palautti HTTP {response.status_code}.")
        try:
            return response.json()
        except ValueError as exc:
            raise TravelError("Digitransitin vastaus ei ollut kelvollista JSONia.") from exc


def parse_geocode_response(payload: Any) -> Coordinates:
    """Poimi ensimmäinen osuma. Testattavissa ilman verkkoa."""
    if not isinstance(payload, dict):
        raise TravelError("Osoitetta ei löytynyt.")
    features = payload.get("features")
    if not isinstance(features, list) or not features:
        raise TravelError("Osoitetta ei löytynyt.")
    geometry = features[0].get("geometry") if isinstance(features[0], dict) else None
    coords = geometry.get("coordinates") if isinstance(geometry, dict) else None
    if not isinstance(coords, list) or len(coords) < 2:
        raise TravelError("Osoitetta ei löytynyt.")
    try:
        longitude = float(coords[0])
        latitude = float(coords[1])
    except (TypeError, ValueError) as exc:
        raise TravelError("Osoitetta ei löytynyt.") from exc
    return Coordinates(latitude=latitude, longitude=longitude)


def parse_plan_duration(payload: Any) -> int:
    """Ensimmäisen reitin kesto sekunteina."""
    if not isinstance(payload, dict):
        raise TravelError("Reittiä Pasilaan ei löytynyt.")
    if payload.get("errors"):
        raise TravelError("Reititys epäonnistui.")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise TravelError("Reittiä Pasilaan ei löytynyt.")
    connection = data.get("planConnection")
    if not isinstance(connection, dict):
        raise TravelError("Reittiä Pasilaan ei löytynyt.")
    edges = connection.get("edges")
    if not isinstance(edges, list) or not edges:
        raise TravelError("Reittiä Pasilaan ei löytynyt.")
    node = edges[0].get("node") if isinstance(edges[0], dict) else None
    if not isinstance(node, dict):
        raise TravelError("Reittiä Pasilaan ei löytynyt.")
    start = node.get("start")
    end = node.get("end")
    if isinstance(start, str) and isinstance(end, str):
        try:
            started = datetime.fromisoformat(start.replace("Z", "+00:00"))
            ended = datetime.fromisoformat(end.replace("Z", "+00:00"))
            seconds = int((ended - started).total_seconds())
            if seconds > 0:
                return seconds
        except ValueError:
            pass
    legs = node.get("legs")
    if isinstance(legs, list):
        total = 0
        for leg in legs:
            if isinstance(leg, dict) and isinstance(leg.get("duration"), (int, float)):
                total += int(leg["duration"])
        if total > 0:
            return total
    raise TravelError("Reittiä Pasilaan ei löytynyt.")


def resolve_travel_seconds(
    store: Any,
    client: DigitransitClient,
    address: str,
) -> int:
    """Geokoodaa kerran ja reititä kävellen; tulos välimuistiin SQLiteen."""
    cleaned = address.strip()
    if not cleaned:
        raise TravelError("Osoite puuttuu.")
    cached = store.cached_travel_seconds(cleaned, _WALK_MODE)
    if cached is not None:
        return cached
    coords = store.cached_coordinates(cleaned)
    if coords is None:
        coords = client.geocode_address(cleaned)
        store.save_coordinates(cleaned, coords)
    seconds = client.travel_seconds(coords)
    store.save_travel_seconds(cleaned, _WALK_MODE, seconds)
    return seconds
