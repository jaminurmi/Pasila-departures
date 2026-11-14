"""Yhteiset näyttötekstit konsolille ja Streamlitille."""

from __future__ import annotations

from datetime import datetime

from pasila_board.processing import Departure

MISSING_TRACK = "—"
MISSING_ESTIMATE = "—"


def format_destination(item: Departure) -> str:
    """Päämäärän nimi ja asemakoodi, jotta HKI ja LEN erottuvat."""
    if item.destination_code:
        return f"{item.destination_name} ({item.destination_code})"
    return item.destination_name or "—"


def format_scheduled(item: Departure) -> str:
    """Aikataulun mukainen lähtö kellonaikana."""
    return item.scheduled_local.strftime("%H:%M")


def format_estimate(item: Departure) -> str:
    """Ennuste, peruttu-merkintä tai viiva jos ennustetta ei ole."""
    if item.cancelled:
        return "peruttu"
    if item.unknown_delay:
        return "myöhässä"
    if item.estimate_local is None:
        return MISSING_ESTIMATE
    clock = item.estimate_local.strftime("%H:%M")
    if item.is_delayed and item.delay_minutes:
        return f"{clock} (+{item.delay_minutes} min)"
    return clock


LEAVE_HOME_MISSED = "ei ehdi"


def format_leave_home(deadline: datetime | None, *, cancelled: bool) -> str:
    """Kelloaika kotoa tai ei ehdi / viiva."""
    if cancelled:
        return MISSING_ESTIMATE
    if deadline is None:
        return LEAVE_HOME_MISSED
    return deadline.strftime("%H:%M")
