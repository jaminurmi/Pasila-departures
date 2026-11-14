"""Konsoliesitys Rich-taulukkona."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from pasila_board.display import (
    MISSING_TRACK,
    format_destination,
    format_scheduled,
)
from pasila_board.processing import Departure


def render_departures(
    departures: list[Departure],
    *,
    station_name: str,
    attribution: str,
    console: Console | None = None,
) -> None:
    """Tulosta lähdöt taulukkona. Perutut punaisina, myöhässä keltaisina."""
    out = console or Console()
    table = Table(
        title=f"Lähtevät lähijunat — {station_name}",
        caption=attribution,
        show_lines=False,
    )
    table.add_column("Linja", justify="center", style="bold", width=5)
    table.add_column("Määränpää")
    table.add_column("Lähtö", justify="center", width=12)
    table.add_column("Raide", justify="center", width=5)

    if not departures:
        table.add_row("—", "Ei lähteviä lähijunia", "—", "—")
        out.print(table)
        return

    for item in departures:
        table.add_row(
            item.line_id or "—",
            format_destination(item),
            format_scheduled(item),
            item.track or MISSING_TRACK,
            style=_row_style(item),
        )
    out.print(table)


def _row_style(item: Departure) -> str:
    if item.cancelled:
        return "bold red"
    if item.is_delayed:
        return "bold red"
    return ""
