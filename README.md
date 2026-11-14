# Pasila departures

Shows the next departing commuter trains from Pasila (PSL) using Digitraffic’s open Rail API. The table lists line, destination, departure time (Europe/Helsinki), estimate, and track. Cancelled rows are red; delayed rows are yellow.

The console prints the next 15 departures. The Streamlit view refreshes every 30 seconds and stores departures in SQLite for delay statistics.

## Setup

Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt
```

In Windows PowerShell, activate the virtual environment with `.venv\Scripts\Activate.ps1`.

## Run

Console (Pasila’s next 15 departures; also writes to SQLite):

```bash
python -m pasila_board
```

Streamlit (30 s refresh, statistics):

```bash
streamlit run app.py
```

The database is created at `data/departures.sqlite`. The unique key is train number + departure date (`departureDate`) + station. The same train is updated when the estimate changes.

## Tests

```bash
python -m pytest
```

## Sources

Train data: [Digitraffic Rail API](https://www.digitraffic.fi/rautatieliikenne/) / Fintraffic, licence [CC 4.0 BY](https://www.digitraffic.fi/kayttoehdot/).

The terms of use require a `Digitraffic-User` header; this app sends `pasila-board/0.1`.
