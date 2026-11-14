# Pasila departures

Shows the next departing commuter trains from Pasila (PSL) using Digitraffic’s open Rail API. The table lists line, destination, departure time (Europe/Helsinki, with +minutes when delayed), track, and — when an address is set — the latest time to leave home. Cancelled and delayed rows are red; trains you can no longer catch are gray.

The console prints the next 15 departures. The Streamlit view refreshes every 30 seconds, filters by direction (Helsinki central station or Airport), stores a local user profile, and keeps delay statistics in SQLite.

## Setup

Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt
```

In Windows PowerShell, activate the virtual environment with `.venv\Scripts\Activate.ps1`.

Copy `.env.example` to `.env` and add a Digitransit subscription key (needed for geocoding and travel time):

```bash
cp .env.example .env
```

Register at the [Digitransit API portal](https://digitransit.fi/en/developers/api-registration/) and subscribe to the Geocoding and Routing products. The key is sent as `digitransit-subscription-key`. Do not commit `.env`.

## Run

Console (Pasila’s next 15 departures; also writes to SQLite):

```bash
python -m pasila_board
```

Streamlit (profile, direction, 30 s refresh, leave-home column, statistics):

```bash
streamlit run app.py
```

The database is created at `data/departures.sqlite`. The unique key for trains is train number + departure date (`departureDate`) + station. Geocoding and travel times are cached locally; the name is never sent to Digitransit.

Leave-home time is train time (live estimate if present) minus travel time minus a 3-minute buffer (`leave_home_buffer_minutes` in settings).

## Tests

```bash
python -m pytest
```

## Sources

Train data: [Digitraffic Rail API](https://www.digitraffic.fi/rautatieliikenne/) / Fintraffic, licence [CC 4.0 BY](https://www.digitraffic.fi/kayttoehdot/). The app sends the required `Digitraffic-User` header (`pasila-board/0.1`).

Geocoding and walking time: [Digitransit](https://digitransit.fi/en/developers/) / HSL (Geocoding REST + Routing GraphQL `planConnection`). Chosen because it has Finnish address data and walking routes in the Helsinki region. Nominatim is geocoding-only and has a strict 1 request/s usage policy.
