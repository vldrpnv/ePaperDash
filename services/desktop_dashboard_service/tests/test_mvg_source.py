from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import unquote

import pytest

from epaper_dashboard_service.adapters.sources.mvg import MvgDepartureSourcePlugin, _parse_time


# ---------------------------------------------------------------------------
# Helper fake fetcher
# ---------------------------------------------------------------------------

_STATION_RESPONSE = [{"globalId": "de:09174:6840", "name": "Eichenau"}]

_PLANNED_MS = 1_714_730_400_000  # 2024-05-03 10:00:00 UTC
_ACTUAL_MS = 1_714_730_580_000   # 2024-05-03 10:03:00 UTC (3 min delay)

_DEPARTURE_ON_TIME = {
    "label": "S4",
    "destination": "Leuchtenbergring",
    "plannedDepartureTime": _PLANNED_MS,
    "realtimeDepartureTime": _PLANNED_MS,
    "cancelled": False,
    "delayInMinutes": 0,
}

_DEPARTURE_DELAYED = {
    "label": "S4",
    "destination": "Leuchtenbergring",
    "plannedDepartureTime": _PLANNED_MS,
    "realtimeDepartureTime": _ACTUAL_MS,
    "cancelled": False,
    "delayInMinutes": 3,
}

_DEPARTURE_CANCELLED = {
    "label": "S3",
    "destination": "Holzkirchen",
    "plannedDepartureTime": _PLANNED_MS,
    "realtimeDepartureTime": None,
    "cancelled": True,
    "delayInMinutes": None,
}


def _make_fetcher(*departure_responses):
    responses = list(departure_responses)
    call_count = [0]

    def fetcher(url: str):
        if "station" in url or "locations" in url:
            assert "Eichenau" in url
            return _STATION_RESPONSE
        resp = responses[call_count[0] % len(responses)]
        call_count[0] += 1
        return resp

    return fetcher


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_mvg_source_requires_station_name() -> None:
    plugin = MvgDepartureSourcePlugin(fetcher=lambda url: [])
    with pytest.raises(ValueError, match="station_name"):
        plugin.fetch({})


def test_mvg_source_looks_up_station_and_uses_global_id() -> None:
    visited_urls: list[str] = []

    def fetcher(url: str):
        visited_urls.append(url)
        if "station" in url or "locations" in url:
            return _STATION_RESPONSE
        return [_DEPARTURE_ON_TIME]

    plugin = MvgDepartureSourcePlugin(fetcher=fetcher)
    plugin.fetch({"station_name": "Eichenau", "limit": 1})

    assert any("Eichenau" in u for u in visited_urls), "station lookup URL should contain query"
    # globalId may be percent-encoded in the URL
    assert any("de:09174:6840" in unquote(u) for u in visited_urls), "departure URL should contain globalId"


def test_mvg_source_raises_when_station_not_found() -> None:
    def fetcher(url: str):
        if "station" in url or "locations" in url:
            return []
        return []

    plugin = MvgDepartureSourcePlugin(fetcher=fetcher)
    with pytest.raises(ValueError, match="station not found"):
        plugin.fetch({"station_name": "Nonexistent"})


def test_mvg_source_maps_on_time_departure() -> None:
    plugin = MvgDepartureSourcePlugin(fetcher=_make_fetcher([_DEPARTURE_ON_TIME]))
    result = plugin.fetch({"station_name": "Eichenau", "limit": 1})

    assert result.station_name == "Eichenau"
    assert len(result.entries) == 1
    dep = result.entries[0]
    assert dep.line == "S4"
    assert dep.destination == "Leuchtenbergring"
    assert dep.scheduled_time == datetime(2024, 5, 3, 10, 0, 0, tzinfo=timezone.utc)
    assert dep.actual_time == datetime(2024, 5, 3, 10, 0, 0, tzinfo=timezone.utc)
    assert not dep.cancelled


def test_mvg_source_maps_delayed_departure() -> None:
    plugin = MvgDepartureSourcePlugin(fetcher=_make_fetcher([_DEPARTURE_DELAYED]))
    result = plugin.fetch({"station_name": "Eichenau", "limit": 1})

    dep = result.entries[0]
    assert dep.actual_time == datetime(2024, 5, 3, 10, 3, 0, tzinfo=timezone.utc)
    assert not dep.cancelled


def test_mvg_source_maps_cancelled_departure() -> None:
    plugin = MvgDepartureSourcePlugin(fetcher=_make_fetcher([_DEPARTURE_CANCELLED]))
    result = plugin.fetch({"station_name": "Eichenau", "limit": 1})

    dep = result.entries[0]
    assert dep.line == "S3"
    assert dep.cancelled
    assert dep.actual_time is None


def test_mvg_source_accepts_wrapped_departures_response() -> None:
    """API may wrap the list inside a 'departures' key."""
    def fetcher(url: str):
        if "station" in url or "locations" in url:
            return _STATION_RESPONSE
        return {"departures": [_DEPARTURE_ON_TIME]}

    plugin = MvgDepartureSourcePlugin(fetcher=fetcher)
    result = plugin.fetch({"station_name": "Eichenau", "limit": 1})
    assert len(result.entries) == 1


def test_mvg_source_accepts_iso_string_times() -> None:
    """Departure times may be ISO-8601 strings instead of epoch milliseconds."""
    raw = dict(_DEPARTURE_ON_TIME)
    raw["plannedDepartureTime"] = "2024-05-03T10:00:00Z"
    raw["realtimeDepartureTime"] = "2024-05-03T10:03:00Z"

    plugin = MvgDepartureSourcePlugin(fetcher=_make_fetcher([raw]))
    result = plugin.fetch({"station_name": "Eichenau", "limit": 1})

    dep = result.entries[0]
    assert dep.scheduled_time == datetime(2024, 5, 3, 10, 0, 0, tzinfo=timezone.utc)
    assert dep.actual_time == datetime(2024, 5, 3, 10, 3, 0, tzinfo=timezone.utc)


def test_parse_time_epoch_ms() -> None:
    result = _parse_time(1_714_730_400_000)
    assert result == datetime(2024, 5, 3, 10, 0, 0, tzinfo=timezone.utc)


def test_parse_time_iso_string() -> None:
    result = _parse_time("2024-05-03T10:00:00Z")
    assert result == datetime(2024, 5, 3, 10, 0, 0, tzinfo=timezone.utc)
