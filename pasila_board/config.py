"""Sovelluksen vakioasetukset. Älä hardkoodaa samoja arvoja muualle."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Digitraffic-kutsujen ja näytön asetukset."""

    base_url: str = "https://rata.digitraffic.fi/api/v1"
    station_code: str = "PSL"
    digitraffic_user: str = "pasila-board/0.1"
    request_timeout_seconds: float = 10.0
    # Rajapinnan suositus: älä kysele tiheämmin kuin data päivittyy.
    refresh_interval_seconds: int = 30
    departing_trains: int = 40
    display_limit: int = 15
    train_categories: str = "Commuter"
    timezone_name: str = "Europe/Helsinki"
    database_path: Path = Path("data/departures.sqlite")
    # Digitrafficin nimet ("Helsinki asema", "Lentoasema") korvataan näytössä.
    station_display_names: dict[str, str] = field(
        default_factory=lambda: {
            "HKI": "Päärautatieasema",
            "LEN": "Lentokenttä",
        }
    )
    # P/I-junat palaavat Pasilaan: suunnan päämäärä on LEN tai HKI, ei reitin loppua.
    destination_hub_codes: tuple[str, ...] = ("LEN", "HKI")
    source_attribution: str = (
        "Lähde: Digitraffic / Fintraffic (rata.digitraffic.fi), lisenssi CC 4.0 BY"
    )


SETTINGS = Settings()
