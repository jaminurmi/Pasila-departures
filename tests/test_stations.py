"""Asemahakemiston testit ilman verkkokutsuja."""

from pasila_board.stations import StationDirectory, _index_station_names


class FakeClient:
    def fetch_stations(self) -> list[dict]:
        return [
            {
                "stationShortCode": "HKI",
                "stationName": "Helsinki asema",
                "passengerTraffic": True,
            },
            {
                "stationShortCode": "PSL",
                "stationName": "Pasila asema",
                "passengerTraffic": True,
            },
            {
                "stationShortCode": "KRM",
                "stationName": "Kärpänen",
                "passengerTraffic": False,
            },
        ]


def test_index_station_names_maps_code_to_name() -> None:
    names = _index_station_names(FakeClient().fetch_stations())
    assert names["HKI"] == "Helsinki asema"


def test_name_for_uses_metadata_or_code() -> None:
    directory = StationDirectory(FakeClient())  # type: ignore[arg-type]
    assert directory.name_for("PSL") == "Pasila asema"
    assert directory.name_for("XYZ") == "XYZ"


def test_display_names_override_metadata() -> None:
    directory = StationDirectory(  # type: ignore[arg-type]
        FakeClient(),
        {"HKI": "Päärautatieasema", "LEN": "Lentokenttä"},
    )
    assert directory.name_for("HKI") == "Päärautatieasema"
    assert directory.name_for("PSL") == "Pasila asema"
