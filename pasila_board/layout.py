"""Streamlit-ulkoasu: yläpalkki ja taulun tiivis asettelu."""

from __future__ import annotations

import html

import streamlit as st

from pasila_board.config import Settings
from pasila_board.storage import UserProfile

_PAGE_CSS = """
<style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 1100px;
    }
    .pasila-app-name {
        font-size: 1.35rem;
        font-weight: 650;
        margin: 0;
        line-height: 1.25;
    }
    .pasila-station {
        margin: 0.15rem 0 0 0;
        color: #444;
        line-height: 1.3;
    }
    .pasila-user-name {
        font-weight: 600;
        text-align: right;
        margin: 0;
        line-height: 1.25;
    }
    .pasila-user-address {
        text-align: right;
        margin: 0.15rem 0 0 0;
        color: #444;
        font-size: 0.9rem;
        line-height: 1.3;
    }
    .pasila-profile-hint {
        color: inherit;
        opacity: 0.65;
        font-size: 0.85rem;
        line-height: 1.35;
        margin: 0.75rem 0 0 0;
        display: flex;
        gap: 0.4rem;
        align-items: flex-start;
    }
    .pasila-profile-hint svg {
        flex-shrink: 0;
        margin-top: 0.12rem;
    }
</style>
"""

_INFO_ICON = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" '
    'viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
    'aria-hidden="true">'
    '<circle cx="12" cy="12" r="10"></circle>'
    '<path d="M12 16v-4"></path><path d="M12 8h.01"></path>'
    "</svg>"
)

ADDRESS_HINT = "Lisää osoite, jotta lähtöaika kotoa voidaan laskea."


def apply_page_chrome(settings: Settings) -> None:
    """Sivun leveys, otsikko ja tiiviimpi reunus."""
    st.set_page_config(
        page_title=settings.app_name,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(_PAGE_CSS, unsafe_allow_html=True)


def render_top_bar(
    *,
    app_name: str,
    station_name: str,
    given_name: str = "",
    family_name: str = "",
    address: str = "",
) -> None:
    """Yläpalkki: vasemmalla sovellus ja asema, oikealla käyttäjä."""
    full_name = " ".join(part for part in (given_name, family_name) if part).strip()
    with st.container():
        left, right = st.columns([2, 1], vertical_alignment="top")
        with left:
            st.markdown(
                f'<p class="pasila-app-name">{html.escape(app_name)}</p>'
                f'<p class="pasila-station">{html.escape(station_name)}</p>',
                unsafe_allow_html=True,
            )
        with right:
            st.markdown(
                f'<p class="pasila-user-name">'
                f'{html.escape(full_name) if full_name else "Ei nimeä"}</p>'
                f'<p class="pasila-user-address">'
                f'{html.escape(address) if address else "Ei osoitetta"}</p>',
                unsafe_allow_html=True,
            )
    st.divider()


def render_profile_form(
    profile: UserProfile,
    settings: Settings,
) -> UserProfile | None:
    """Sivupalkin lomake. Palauttaa uuden profiilin vain tallennuksessa."""
    labels = settings.direction_labels
    codes = list(labels)
    default_index = (
        codes.index(profile.direction_code)
        if profile.direction_code in labels
        else codes.index(settings.default_direction_code)
        if settings.default_direction_code in labels
        else 0
    )
    with st.sidebar:
        st.header("Profiili")
        with st.form("user_profile"):
            given_name = st.text_input("Etunimi", value=profile.given_name)
            family_name = st.text_input("Sukunimi", value=profile.family_name)
            address = st.text_input("Osoite", value=profile.address)
            direction_code = st.radio(
                "Suunta",
                options=codes,
                index=default_index,
                format_func=lambda code: labels[code],
            )
            submitted = st.form_submit_button("Tallenna")
        if not profile.address.strip():
            st.markdown(
                f'<p class="pasila-profile-hint">{_INFO_ICON}'
                f"<span>{html.escape(ADDRESS_HINT)}</span></p>",
                unsafe_allow_html=True,
            )
    if not submitted:
        return None
    chosen = direction_code if direction_code in labels else settings.default_direction_code
    return UserProfile(
        given_name=given_name,
        family_name=family_name,
        address=address,
        direction_code=chosen,
    )
