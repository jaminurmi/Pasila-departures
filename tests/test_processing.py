"""Käsittelylogiikan testit ilman HTTP-kutsuja."""

from datetime import datetime
from zoneinfo import ZoneInfo

from pasila_board.display import MISSING_TRACK, format_estimate
from pasila_board.processing import (
    build_departures,
    stops_at_after_departure,
    utc_to_helsinki,
)

HELSINKI = "Europe/Helsinki"


def _name_for(code: str) -> str:
    names = {"HKI": "Helsinki asema", "LEN": "Lentoasema", "PSL": "Pasila asema"}
    return names.get(code, code)


def _row(
    *,
    station: str,
    row_type: str,
    scheduled: str,
    commercial_stop: bool = True,
    train_stopping: bool = True,
    cancelled: bool = False,
    track: str | None = "10",
    estimate: str | None = None,
    actual: str | None = None,
    delay: int | None = None,
    unknown_delay: bool | None = None,
) -> dict:
    row: dict = {
        "stationShortCode": station,
        "type": row_type,
        "scheduledTime": scheduled,
        "commercialStop": commercial_stop,
        "trainStopping": train_stopping,
        "cancelled": cancelled,
        "commercialTrack": track,
    }
    if estimate is not None:
        row["liveEstimateTime"] = estimate
    if actual is not None:
        row["actualTime"] = actual
    if delay is not None:
        row["differenceInMinutes"] = delay
    if unknown_delay is not None:
        row["unknownDelay"] = unknown_delay
    return row


def test_utc_to_helsinki_winter_time() -> None:
    """Marraskuussa Suomi on UTC+2 (EET)."""
    local = utc_to_helsinki("2026-11-14T12:18:00.000Z", HELSINKI)
    assert local.tzinfo is not None
    assert local.isoformat() == "2026-11-14T14:18:00+02:00"


def test_missing_track_becomes_none() -> None:
    now = datetime(2026, 11, 14, 12, 0, tzinfo=ZoneInfo(HELSINKI))
    trains = [
        {
            "trainNumber": 1,
            "departureDate": "2026-11-14",
            "commuterLineID": "A",
            "cancelled": False,
            "timeTableRows": [
                _row(
                    station="PSL",
                    row_type="DEPARTURE",
                    scheduled="2026-11-14T12:18:00.000Z",
                    track="",
                ),
                _row(
                    station="HKI",
                    row_type="ARRIVAL",
                    scheduled="2026-11-14T12:23:00.000Z",
                ),
            ],
        }
    ]
    result = build_departures(
        trains,
        station_code="PSL",
        name_for=_name_for,
        timezone_name=HELSINKI,
        now=now,
        limit=15,
    )
    assert len(result) == 1
    assert result[0].track is None
    assert (result[0].track or MISSING_TRACK) == "—"


def test_cancelled_train_is_not_marked_delayed() -> None:
    now = datetime(2026, 11, 14, 12, 0, tzinfo=ZoneInfo(HELSINKI))
    trains = [
        {
            "trainNumber": 2,
            "departureDate": "2026-11-14",
            "commuterLineID": "K",
            "cancelled": True,
            "timeTableRows": [
                _row(
                    station="PSL",
                    row_type="DEPARTURE",
                    scheduled="2026-11-14T12:30:00.000Z",
                    cancelled=True,
                    delay=12,
                    estimate="2026-11-14T12:42:00.000Z",
                ),
                _row(
                    station="HKI",
                    row_type="ARRIVAL",
                    scheduled="2026-11-14T12:35:00.000Z",
                    cancelled=True,
                ),
            ],
        }
    ]
    result = build_departures(
        trains,
        station_code="PSL",
        name_for=_name_for,
        timezone_name=HELSINKI,
        now=now,
        limit=15,
    )
    assert len(result) == 1
    assert result[0].cancelled is True
    assert result[0].is_delayed is False
    assert format_estimate(result[0]) == "peruttu"


def test_p_train_keeps_second_pasila_departure() -> None:
    """Ensimmäisen Pasilan lähdön toteuduttua jälkimmäinen jää listaan."""
    now = datetime(2026, 11, 14, 14, 30, tzinfo=ZoneInfo(HELSINKI))
    trains = [
        {
            "trainNumber": 8681,
            "departureDate": "2026-11-14",
            "commuterLineID": "P",
            "cancelled": False,
            "timeTableRows": [
                _row(
                    station="PSL",
                    row_type="DEPARTURE",
                    scheduled="2026-11-14T12:22:30.000Z",
                    actual="2026-11-14T12:22:40.000Z",
                    track="11",
                ),
                _row(
                    station="LEN",
                    row_type="ARRIVAL",
                    scheduled="2026-11-14T12:51:00.000Z",
                ),
                _row(
                    station="PSL",
                    row_type="DEPARTURE",
                    scheduled="2026-11-14T13:16:30.000Z",
                    track="1",
                ),
                _row(
                    station="HKI",
                    row_type="ARRIVAL",
                    scheduled="2026-11-14T13:21:00.000Z",
                ),
            ],
        }
    ]
    result = build_departures(
        trains,
        station_code="PSL",
        name_for=_name_for,
        timezone_name=HELSINKI,
        now=now,
        limit=15,
    )
    assert len(result) == 1
    assert result[0].line_id == "P"
    assert result[0].destination_code == "HKI"
    assert result[0].track == "1"


def test_p_train_outbound_destination_is_len_inbound_is_hki() -> None:
    """Sama P-juna: lentoasemalle LEN, paluu Helsinkiin HKI."""
    now = datetime(2026, 11, 14, 14, 0, tzinfo=ZoneInfo(HELSINKI))
    trains = [
        {
            "trainNumber": 8681,
            "departureDate": "2026-11-14",
            "commuterLineID": "P",
            "cancelled": False,
            "timeTableRows": [
                _row(
                    station="PSL",
                    row_type="DEPARTURE",
                    scheduled="2026-11-14T12:22:30.000Z",
                    track="11",
                ),
                _row(
                    station="LEN",
                    row_type="ARRIVAL",
                    scheduled="2026-11-14T12:51:00.000Z",
                ),
                _row(
                    station="PSL",
                    row_type="ARRIVAL",
                    scheduled="2026-11-14T13:16:06.000Z",
                    track="1",
                ),
                _row(
                    station="PSL",
                    row_type="DEPARTURE",
                    scheduled="2026-11-14T13:16:30.000Z",
                    track="1",
                ),
                _row(
                    station="HKI",
                    row_type="ARRIVAL",
                    scheduled="2026-11-14T13:21:00.000Z",
                ),
            ],
        }
    ]
    result = build_departures(
        trains,
        station_code="PSL",
        name_for=_name_for,
        timezone_name=HELSINKI,
        now=now,
        limit=15,
    )
    assert [(item.destination_code, item.track) for item in result] == [
        ("LEN", "11"),
        ("HKI", "1"),
    ]


def _p_train_both_legs() -> dict:
    return {
        "trainNumber": 8681,
        "departureDate": "2026-11-14",
        "commuterLineID": "P",
        "cancelled": False,
        "timeTableRows": [
            _row(
                station="PSL",
                row_type="DEPARTURE",
                scheduled="2026-11-14T12:22:30.000Z",
                track="11",
            ),
            _row(
                station="LEN",
                row_type="ARRIVAL",
                scheduled="2026-11-14T12:51:00.000Z",
            ),
            _row(
                station="PSL",
                row_type="ARRIVAL",
                scheduled="2026-11-14T13:16:06.000Z",
                track="1",
            ),
            _row(
                station="PSL",
                row_type="DEPARTURE",
                scheduled="2026-11-14T13:16:30.000Z",
                track="1",
            ),
            _row(
                station="HKI",
                row_type="ARRIVAL",
                scheduled="2026-11-14T13:21:00.000Z",
            ),
        ],
    }


def test_stops_at_len_after_outbound_pasila_departure() -> None:
    rows = _p_train_both_legs()["timeTableRows"]
    assert stops_at_after_departure(rows, 0, "PSL", "LEN") is True
    assert stops_at_after_departure(rows, 0, "PSL", "HKI") is False


def test_stops_at_hki_after_inbound_pasila_departure() -> None:
    rows = _p_train_both_legs()["timeTableRows"]
    assert stops_at_after_departure(rows, 3, "PSL", "HKI") is True
    assert stops_at_after_departure(rows, 3, "PSL", "LEN") is False


def test_direction_filter_keeps_only_trains_that_stop_at_target() -> None:
    now = datetime(2026, 11, 14, 14, 0, tzinfo=ZoneInfo(HELSINKI))
    westbound = {
        "trainNumber": 1,
        "departureDate": "2026-11-14",
        "commuterLineID": "A",
        "cancelled": False,
        "timeTableRows": [
            _row(
                station="PSL",
                row_type="DEPARTURE",
                scheduled="2026-11-14T12:27:00.000Z",
                track="11",
            ),
            _row(
                station="LPV",
                row_type="ARRIVAL",
                scheduled="2026-11-14T12:40:00.000Z",
            ),
        ],
    }
    common = dict(
        station_code="PSL",
        name_for=_name_for,
        timezone_name=HELSINKI,
        now=now,
        limit=15,
    )
    to_airport = build_departures(
        [_p_train_both_legs(), westbound],
        via_station_code="LEN",
        **common,
    )
    to_helsinki = build_departures(
        [_p_train_both_legs(), westbound],
        via_station_code="HKI",
        **common,
    )
    assert [item.destination_code for item in to_airport] == ["LEN"]
    assert [item.destination_code for item in to_helsinki] == ["HKI"]
