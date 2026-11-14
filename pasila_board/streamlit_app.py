"""Streamlit-näkymä: Pasilan automaattisesti päivittyvä lähtötaulu."""

from __future__ import annotations

import streamlit as st

from pasila_board.board import load_departure_board
from pasila_board.client import DigitrafficClient, DigitrafficError
from pasila_board.config import SETTINGS
from pasila_board.stations import StationDirectory
from pasila_board.storage import DepartureStore
from pasila_board.web_table import departures_frame, stats_frame, style_departure_rows


@st.cache_resource
def _client() -> DigitrafficClient:
    return DigitrafficClient(SETTINGS)


@st.cache_resource
def _stations(display_key: str) -> StationDirectory:
    return StationDirectory(_client(), SETTINGS.station_display_names)


def _station_directory() -> StationDirectory:
    display_key = "|".join(
        f"{code}:{name}"
        for code, name in sorted(SETTINGS.station_display_names.items())
    )
    return _stations(display_key)


@st.cache_resource
def _store() -> DepartureStore:
    return DepartureStore(SETTINGS.database_path)


def main() -> None:
    """Piirrä sivu: taulu päivittyy fragmentissa."""
    st.set_page_config(page_title="Lähtevät lähijunat", layout="centered")
    st.title("Lähtevät lähijunat")
    departing_board()
    st.caption(SETTINGS.source_attribution)


@st.fragment(run_every=SETTINGS.refresh_interval_seconds)
def departing_board() -> None:
    """Päivitä Pasilan lähtötaulu ilman koko sivun uudelleenajoa."""
    _render_live_table()


def _render_live_table() -> None:
    station_code = SETTINGS.station_code
    try:
        board = load_departure_board(
            _client(),
            _station_directory(),
            SETTINGS,
            station_code,
            _store(),
        )
    except DigitrafficError as exc:
        st.error(str(exc))
        _render_delay_stats(station_code)
        return

    st.subheader(board.station_name)
    if not board.departures:
        st.info("Ei lähteviä lähijunia.")
    else:
        st.dataframe(
            style_departure_rows(departures_frame(board.departures)),
            hide_index=True,
            width="stretch",
        )

    _render_delay_stats(station_code)


def _render_delay_stats(station_code: str) -> None:
    """Näytä tallennetut myöhästymiset linjoittain ja kellonajoittain."""
    store = _store()
    by_line = store.delay_stats_by_line(station_code)
    by_hour = store.delay_stats_by_hour(station_code)
    st.subheader("Myöhästymistilasto")
    if not by_line and not by_hour:
        st.info("Ei vielä tilastoja tältä asemalta.")
        return

    left, right = st.columns(2)
    with left:
        st.caption("Linjoittain")
        if by_line:
            st.dataframe(stats_frame(by_line, "Linja"), hide_index=True, width="stretch")
        else:
            st.info("Ei linjatilastoja.")
    with right:
        st.caption("Kellonajoittain")
        if by_hour:
            st.dataframe(
                stats_frame(by_hour, "Kello"),
                hide_index=True,
                width="stretch",
            )
        else:
            st.info("Ei kellonaikatilastoja.")


if __name__ == "__main__":
    main()
