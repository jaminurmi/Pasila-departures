"""Streamlit-näkymä: Pasilan automaattisesti päivittyvä lähtötaulu."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

from pasila_board.board import load_departure_board
from pasila_board.client import DigitrafficClient, DigitrafficError
from pasila_board.config import SETTINGS
from pasila_board.layout import apply_page_chrome, render_profile_form, render_top_bar
from pasila_board.stations import StationDirectory
from pasila_board.storage import DepartureStore
from pasila_board.travel import DigitransitClient, TravelError, resolve_travel_seconds
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
def _store(schema_version: int = 4) -> DepartureStore:
    return DepartureStore(SETTINGS.database_path)


@st.cache_resource
def _travel_client() -> DigitransitClient:
    return DigitransitClient(SETTINGS)


def main() -> None:
    """Piirrä sivu: yläpalkki pysyy, taulu päivittyy fragmentissa."""
    apply_page_chrome(SETTINGS)
    store = _store(4)
    profile = store.load_profile()
    updated = render_profile_form(profile, SETTINGS)
    if updated is not None:
        store.save_profile(updated)
        profile = updated
    travel_seconds, travel_error = _travel_seconds_or_error(store, profile)
    render_top_bar(
        app_name=SETTINGS.app_name,
        station_name=SETTINGS.station_display_names.get(
            SETTINGS.station_code,
            SETTINGS.station_code,
        ),
        given_name=profile.given_name,
        family_name=profile.family_name,
        address=profile.address,
    )
    departing_board(profile.direction_code, travel_seconds, travel_error)
    st.caption(SETTINGS.source_attribution)


def _travel_seconds_or_error(
    store: DepartureStore,
    profile,
) -> tuple[int | None, str | None]:
    if not profile.address.strip():
        return None, None
    try:
        seconds = resolve_travel_seconds(
            store,
            _travel_client(),
            profile.address,
        )
    except TravelError as exc:
        message = str(exc)
        if _should_hide_leave_home(message):
            return None, None
        return None, message
    except Exception:
        return None, None
    return seconds, None


def _should_hide_leave_home(message: str) -> bool:
    """Osoitetta tai reittiä ei löydy: piilota sarake, älä kaada sivua."""
    hidden_markers = (
        "Osoitetta ei löytynyt",
        "Reittiä Pasilaan ei löytynyt",
        "Reititys epäonnistui",
    )
    return any(marker in message for marker in hidden_markers)


@st.fragment(run_every=SETTINGS.refresh_interval_seconds)
def departing_board(
    via_station_code: str,
    travel_seconds: int | None,
    travel_error: str | None,
) -> None:
    """Päivitä Pasilan lähtötaulu ilman koko sivun uudelleenajoa."""
    _render_live_table(via_station_code, travel_seconds, travel_error)


def _render_live_table(
    via_station_code: str,
    travel_seconds: int | None,
    travel_error: str | None,
) -> None:
    station_code = SETTINGS.station_code
    try:
        board = load_departure_board(
            _client(),
            _station_directory(),
            SETTINGS,
            station_code,
            _store(4),
            via_station_code=via_station_code,
        )
    except DigitrafficError as exc:
        st.error(str(exc))
        _render_delay_stats(station_code)
        return

    if travel_error:
        st.warning(travel_error)

    if not board.departures:
        st.info("Ei lähteviä lähijunia.")
    else:
        now = datetime.now(ZoneInfo(SETTINGS.timezone_name))
        frame = departures_frame(
            board.departures,
            travel_seconds=travel_seconds,
            buffer_minutes=SETTINGS.leave_home_buffer_minutes,
            now=now if travel_seconds is not None else None,
        )
        st.dataframe(
            style_departure_rows(frame),
            hide_index=True,
            width="stretch",
            height="content",
            row_height=SETTINGS.table_row_height_px,
        )

    _render_delay_stats(station_code)


def _render_delay_stats(station_code: str) -> None:
    """Näytä tallennetut myöhästymiset linjoittain ja kellonajoittain."""
    store = _store(4)
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
