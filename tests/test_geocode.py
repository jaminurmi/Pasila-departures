"""Geokoodausvastauksen käsittely ilman HTTP-kutsuja."""

import pytest

from pasila_board.travel import TravelError, parse_geocode_response, parse_plan_duration


def test_empty_geocode_features_raises() -> None:
    with pytest.raises(TravelError, match="Osoitetta ei löytynyt"):
        parse_geocode_response({"features": []})


def test_missing_geocode_payload_raises() -> None:
    with pytest.raises(TravelError, match="Osoitetta ei löytynyt"):
        parse_geocode_response(None)


def test_geocode_reads_geojson_coordinates() -> None:
    coords = parse_geocode_response(
        {
            "features": [
                {"geometry": {"type": "Point", "coordinates": [24.94, 60.19]}}
            ]
        }
    )
    assert coords.longitude == 24.94
    assert coords.latitude == 60.19


def test_empty_plan_edges_raises() -> None:
    with pytest.raises(TravelError, match="Reittiä Pasilaan ei löytynyt"):
        parse_plan_duration({"data": {"planConnection": {"edges": []}}})
