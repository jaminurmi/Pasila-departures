"""Sovelluksen vakioasetukset. Älä hardkoodaa samoja arvoja muualle."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from pasila_board.env_file import load_env_file

load_env_file()


@dataclass(frozen=True)
class Settings:
    """Digitraffic-kutsujen ja näytön asetukset."""

    base_url: str = "https://rata.digitraffic.fi/api/v1"
    station_code: str = "PSL"
    app_name: str = "Pasilan lähdöt"
    digitraffic_user: str = "pasila-board/0.1"
    request_timeout_seconds: float = 10.0
    # Rajapinnan suositus: älä kysele tiheämmin kuin data päivittyy.
    refresh_interval_seconds: int = 30
    departing_trains: int = 40
    max_departing_trains: int = 120
    display_limit: int = 15
    default_direction_code: str = "HKI"
    direction_labels: dict[str, str] = field(
        default_factory=lambda: {
            "HKI": "Helsingin päärautatieasema",
            "LEN": "Lentokenttä",
        }
    )
    train_categories: str = "Commuter"
    timezone_name: str = "Europe/Helsinki"
    database_path: Path = Path("data/departures.sqlite")
    # Digitrafficin nimet ("Helsinki asema", "Lentoasema") korvataan näytössä.
    station_display_names: dict[str, str] = field(
        default_factory=lambda: {
            "PSL": "Pasilan asema",
            "HKI": "Päärautatieasema",
            "LEN": "Lentokenttä",
        }
    )
    # st.dataframe height="auto" näyttää vain 10 riviä; content + rivikorkeus
    # pitää 15 lähtöä näkyvissä ilman taulun sisäistä vieritystä.
    table_row_height_px: int = 28
    # P/I-junat palaavat Pasilaan: suunnan päämäärä on LEN tai HKI, ei reitin loppua.
    destination_hub_codes: tuple[str, ...] = ("LEN", "HKI")
    # Digitraffic-metadatan PSL-koordinaatit (WGS 84).
    pasila_latitude: float = 60.198689
    pasila_longitude: float = 24.933521
    leave_home_buffer_minutes: int = 3
    digitransit_geocode_url: str = "https://api.digitransit.fi/geocoding/v1/search"
    digitransit_routing_url: str = (
        "https://api.digitransit.fi/routing/v2/hsl/gtfs/v1"
    )
    source_attribution: str = (
        "Lähde: Digitraffic / Fintraffic (rata.digitraffic.fi), lisenssi CC 4.0 BY. "
        "Reititys ja geokoodaus: Digitransit / HSL."
    )

    @property
    def digitransit_subscription_key(self) -> str:
        """API-avain ympäristömuuttujasta, ei koodista."""
        return os.environ.get("DIGITRANSIT_SUBSCRIPTION_KEY", "").strip()


SETTINGS = Settings()
