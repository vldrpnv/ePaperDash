from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Protocol
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from epaper_dashboard_service.domain.models import TrainDeparture, TrainDepartures
from epaper_dashboard_service.domain.ports import SourcePlugin


_BASE_URL = "https://www.mvg.de/api/fib/v2/"
_DEFAULT_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; ePaperDash/1.0)",
}


class MvgFetcher(Protocol):
    def __call__(self, url: str) -> Any: ...


class MvgDepartureSourcePlugin(SourcePlugin):
    """Fetch upcoming train departures from a Munich MVG/MVV station.

    Configuration keys:
    - ``station_name`` (required): human-readable station name, e.g. ``"Eichenau"``.
    - ``limit`` (optional, default 5): maximum number of departures to return.
    - ``offset_minutes`` (optional, default 0): skip departures within this many minutes.
    - ``base_url`` (optional): override the MVG API base URL (used in tests).
    """

    name = "mvg_departures"

    def __init__(self, fetcher: MvgFetcher | None = None) -> None:
        self._fetcher = fetcher or _fetch_json

    def fetch(self, config: dict[str, Any]) -> TrainDepartures:
        if "station_name" not in config:
            raise ValueError(f"{self.name} source requires config value: station_name")

        station_name = str(config["station_name"])
        limit = int(config.get("limit", 5))
        offset_minutes = int(config.get("offset_minutes", 0))
        base_url = str(config.get("base_url", _BASE_URL))

        global_id = self._lookup_station(station_name, base_url)
        raw_departures = self._fetch_departures(global_id, limit, offset_minutes, base_url)
        entries = tuple(_parse_departure(d) for d in raw_departures)
        return TrainDepartures(station_name=station_name, entries=entries)

    def _lookup_station(self, name: str, base_url: str) -> str:
        query = urlencode({"query": name})
        url = urljoin(base_url, f"station?{query}")
        data = self._fetcher(url)
        stations = data if isinstance(data, list) else data.get("locations", [])
        if not stations:
            raise ValueError(f"MVG station not found: {name!r}")
        return str(stations[0]["globalId"])

    def _fetch_departures(self, global_id: str, limit: int, offset_minutes: int, base_url: str) -> list[dict[str, Any]]:
        query = urlencode(
            {
                "globalId": global_id,
                "limit": limit,
                "offsetInMinutes": offset_minutes,
            }
        )
        url = urljoin(base_url, f"departure?{query}")
        data = self._fetcher(url)
        # The API may return a list directly or wrap it in a dict.
        if isinstance(data, list):
            return data
        return list(data.get("departures", []))


def _parse_departure(raw: dict[str, Any]) -> TrainDeparture:
    line_field = raw.get("line")
    if isinstance(line_field, dict):
        line = str(line_field.get("label", "?"))
    else:
        line = str(raw.get("label", "?"))

    if isinstance(line_field, dict):
        destination = str(line_field.get("destination", ""))
    else:
        destination = str(raw.get("destination", ""))

    planned = _parse_time(raw.get("plannedDepartureTime") or raw.get("departureTimePlanned"))
    actual_raw = raw.get("realtimeDepartureTime") or raw.get("departureTimeReal")
    actual = _parse_time(actual_raw) if actual_raw is not None else None
    cancelled = bool(raw.get("cancelled", False))

    return TrainDeparture(
        line=line,
        destination=destination,
        scheduled_time=planned,
        actual_time=actual,
        cancelled=cancelled,
    )


def _parse_time(value: Any) -> datetime:
    """Parse either epoch milliseconds (int/float) or ISO-8601 string into a UTC datetime."""
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000.0, tz=timezone.utc)
    if isinstance(value, str):
        # Python 3.11+ handles 'Z' suffix; normalise for older versions.
        normalised = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalised)
    raise ValueError(f"Cannot parse departure time: {value!r}")


def _fetch_json(url: str) -> Any:
    req = Request(url, headers=_DEFAULT_HEADERS)
    with urlopen(req, timeout=10) as response:
        return json.load(response)
