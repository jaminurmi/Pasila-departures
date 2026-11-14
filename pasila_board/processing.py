"""Raaka junadata → näytettävät lähdöt. Ei HTTP-kutsuja."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Iterator
from zoneinfo import ZoneInfo

NameLookup = Callable[[str], str]


@dataclass(frozen=True)
class Departure:
    """Yksi matkustajalähtö valitulta asemalta."""

    train_number: int
    departure_date: str
    line_id: str
    destination_code: str
    destination_name: str
    scheduled_local: datetime
    estimate_local: datetime | None
    track: str | None
    cancelled: bool
    delay_minutes: int | None
    unknown_delay: bool

    @property
    def is_delayed(self) -> bool:
        """Myöhässä, jos ennuste tai erotus on vähintään minuutti."""
        if self.cancelled:
            return False
        if self.unknown_delay:
            return True
        if self.delay_minutes is not None:
            return self.delay_minutes >= 1
        return False


def utc_to_helsinki(utc_timestamp: str, timezone_name: str) -> datetime:
    """Muunna ISO-8601 UTC-aikaleima Europe/Helsinki-aikaan.

    Digitraffic palauttaa ajat muodossa 2026-11-14T12:18:00.000Z.
    """
    normalized = utc_timestamp.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo("UTC"))
    return parsed.astimezone(ZoneInfo(timezone_name))


def build_departures(
    trains: list[dict[str, Any]],
    *,
    station_code: str,
    name_for: NameLookup,
    timezone_name: str,
    now: datetime,
    limit: int,
    hub_codes: tuple[str, ...] = ("LEN", "HKI"),
    via_station_code: str | None = None,
) -> list[Departure]:
    """Poimi tulevat lähdöt, järjestä ajan mukaan ja rajaa määrään."""
    departures: list[Departure] = []
    for train in trains:
        for departure in _departures_from_train(
            train,
            station_code=station_code,
            name_for=name_for,
            timezone_name=timezone_name,
            hub_codes=hub_codes,
            via_station_code=via_station_code,
        ):
            compare_at = (
                departure.scheduled_local
                if departure.cancelled
                else _effective_time(departure)
            )
            if compare_at < now:
                continue
            departures.append(departure)

    departures.sort(key=_effective_time)
    return departures[:limit]


def _departures_from_train(
    train: dict[str, Any],
    *,
    station_code: str,
    name_for: NameLookup,
    timezone_name: str,
    hub_codes: tuple[str, ...],
    via_station_code: str | None,
) -> Iterator[Departure]:
    """Yksi rivi kutakin aseman kaupallista DEPARTURE-tapahtumaa kohti.

    P-juna pysähtyy Pasilassa kahdesti (lentoasemalle ja takaisin Helsinkiin),
    joten koko junaa ei saa hylätä ensimmäisen toteutuneen lähdön takia.
    """
    rows: list[dict[str, Any]] = list(train.get("timeTableRows") or [])
    for index, row in enumerate(rows):
        if not _is_station_departure(row, station_code):
            continue
        if isinstance(row.get("actualTime"), str):
            continue
        if via_station_code and not stops_at_after_departure(
            rows,
            index,
            station_code,
            via_station_code,
        ):
            continue
        departure = _departure_from_row(
            train,
            row,
            row_index=index,
            rows=rows,
            station_code=station_code,
            name_for=name_for,
            timezone_name=timezone_name,
            hub_codes=hub_codes,
        )
        if departure is not None:
            yield departure


def _departure_from_row(
    train: dict[str, Any],
    row: dict[str, Any],
    *,
    row_index: int,
    rows: list[dict[str, Any]],
    station_code: str,
    name_for: NameLookup,
    timezone_name: str,
    hub_codes: tuple[str, ...],
) -> Departure | None:
    scheduled_raw = row.get("scheduledTime")
    if not isinstance(scheduled_raw, str):
        return None

    estimate_raw = row.get("liveEstimateTime")
    estimate_local = (
        utc_to_helsinki(estimate_raw, timezone_name)
        if isinstance(estimate_raw, str)
        else None
    )
    scheduled_local = utc_to_helsinki(scheduled_raw, timezone_name)

    track = row.get("commercialTrack")
    track_value = track.strip() if isinstance(track, str) and track.strip() else None

    delay_minutes = _delay_minutes(row, scheduled_local, estimate_local)
    destination_code = _destination_code(
        rows,
        row_index,
        station_code,
        hub_codes=hub_codes,
    )
    cancelled = bool(train.get("cancelled")) or bool(row.get("cancelled"))

    return Departure(
        train_number=int(train.get("trainNumber", 0)),
        departure_date=str(train.get("departureDate", "")),
        line_id=str(train.get("commuterLineID") or train.get("trainType") or ""),
        destination_code=destination_code,
        destination_name=name_for(destination_code),
        scheduled_local=scheduled_local,
        estimate_local=estimate_local,
        track=track_value,
        cancelled=cancelled,
        delay_minutes=delay_minutes,
        unknown_delay=bool(row.get("unknownDelay")),
    )


def _delay_minutes(
    row: dict[str, Any],
    scheduled_local: datetime,
    estimate_local: datetime | None,
) -> int | None:
    delay = row.get("differenceInMinutes")
    if isinstance(delay, bool):
        return None
    if isinstance(delay, (int, float)):
        return int(delay)
    if estimate_local is not None:
        return int((estimate_local - scheduled_local).total_seconds() // 60)
    return None


def stops_at_after_departure(
    rows: list[dict[str, Any]],
    departure_index: int,
    station_code: str,
    target_code: str,
) -> bool:
    """Pysähtyykö juna kohteessa tämän lähdön jälkeen, ennen paluuta asemalle."""
    for row in _leg_arrivals(rows, departure_index, station_code):
        if row.get("stationShortCode") == target_code and not row.get("cancelled"):
            return True
    return False


def _leg_arrivals(
    rows: list[dict[str, Any]],
    departure_index: int,
    station_code: str,
) -> Iterator[dict[str, Any]]:
    """Kaupalliset saapumiset tämän lähdön jälkeen, kunnes juna palaa asemalle."""
    for row in rows[departure_index + 1 :]:
        if row.get("type") != "ARRIVAL":
            continue
        if row.get("trainStopping") is False:
            continue
        if row.get("commercialStop") is False:
            continue
        code = row.get("stationShortCode")
        if not isinstance(code, str):
            continue
        if code == station_code:
            return
        yield row


def _is_station_departure(row: dict[str, Any], station_code: str) -> bool:
    """Onko rivi aseman kaupallinen lähtö."""
    if row.get("stationShortCode") != station_code:
        return False
    if row.get("type") != "DEPARTURE":
        return False
    if row.get("trainStopping") is False:
        return False
    if row.get("commercialStop") is False:
        return False
    return True


def _destination_code(
    rows: list[dict[str, Any]],
    departure_index: int,
    station_code: str,
    *,
    hub_codes: tuple[str, ...],
) -> str:
    """Päämäärä tälle lähdölle, ei välttämättä koko junan viimeinen asema.

    P-juna kulkee Pasilan kautta lentoasemalle ja takaisin Helsinkiin.
    Rajapinta ei merkitse suuntaa erikseen: suunta päätellään reitistä.
    Jos juna palaa tälle asemalle, käytetään vain sen silmukan pysähdyksiä.
    LEN tai HKI silmukassa voittaa, muuten viimeinen kaupallinen saapuminen.
    """
    last_commercial: str | None = None
    last_active: str | None = None
    last_hub_commercial: str | None = None
    last_hub_active: str | None = None

    for row in _leg_arrivals(rows, departure_index, station_code):
        code = row.get("stationShortCode")
        if not isinstance(code, str):
            continue
        last_commercial = code
        if code in hub_codes:
            last_hub_commercial = code
        if not row.get("cancelled"):
            last_active = code
            if code in hub_codes:
                last_hub_active = code

    return (
        last_hub_active
        or last_hub_commercial
        or last_active
        or last_commercial
        or station_code
    )


def _effective_time(departure: Departure) -> datetime:
    if departure.estimate_local is not None and not departure.cancelled:
        return departure.estimate_local
    return departure.scheduled_local


def leave_home_deadline(
    departure: Departure,
    *,
    travel_seconds: int,
    buffer_minutes: int,
) -> datetime:
    """Viimeinen hetki lähteä kotoa: junan aika miinus matka miinus puskuri.

    Junan aikana käytetään ennustetta, jos se on saatavilla.
    """
    train_at = _effective_time(departure)
    return train_at - timedelta(seconds=travel_seconds) - timedelta(
        minutes=buffer_minutes
    )


def missed_leave_home(deadline: datetime, now: datetime) -> bool:
    """True, jos kotoa pitäisi olla jo lähdetty."""
    return deadline < now
