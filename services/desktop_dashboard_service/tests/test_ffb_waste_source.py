from __future__ import annotations

from datetime import date
from typing import Any, Callable
from urllib.error import URLError

import pytest

from epaper_dashboard_service.adapters.sources.waste import FfbWasteCollectionSourcePlugin
from epaper_dashboard_service.domain.errors import SourceUnavailableError
from epaper_dashboard_service.domain.models import WasteCollectionEntry


_PLACES_RESPONSE = [
    {"key": "place-eichenau", "value": "Eichenau"},
    {"key": "place-ffb", "value": "Fürstenfeldbruck"},
]

_STREETS_RESPONSE = [
    {"key": "street-ring", "value": "Ringstr."},
    {"key": "street-bahnhof", "value": "Bahnhofstr."},
]

_HOUSE_NUMBERS_RESPONSE = [
    {"key": "house-12", "value": "12"},
    {"key": "house-12a", "value": "12a"},
]

_CALENDAR_RESPONSE = {
    "fracts": [
        {"snm": "REST", "nm": "Restmülltonne"},
        {"snm": "BIO", "nm": "Biotonne"},
        {"snm": "PAPIER", "nm": "Papiertonne"},
    ],
    "calendar": [
        {"dt": "20240501", "ad": "Ringstr. 12", "fr": ["REST"]},
        {"dt": "20240502", "ad": "Ringstr. 12", "fr": ["BIO"]},
        {"dt": "20240505", "ad": "Ringstr. 12", "fr": ["PAPIER"]},
    ],
}

_CALENDAR_RESPONSE_WITH_HOLIDAY = {
    "fracts": [
        {"snm": "REST", "nm": "Restmülltonne"},
        {"snm": "BIO", "nm": "Biotonne"},
    ],
    "calendar": [
        {"dt": "20240501", "ad": "Ringstr. 12", "fr": ["REST"]},
        # Public holiday — AWIDO returns fr: null and ft: <name>
        {"dt": "20240502", "ad": None, "fr": None, "ft": "Tag der Arbeit", "id": None},
        {"dt": "20240503", "ad": "Ringstr. 12", "fr": ["BIO"]},
    ],
}


def _make_json_fetcher() -> tuple[list[str], Callable[[str], Any]]:
    visited_urls: list[str] = []

    def fetcher(url: str):
        visited_urls.append(url)
        if "getPlaces" in url:
            return _PLACES_RESPONSE
        if "getGroupedStreets" in url:
            return _STREETS_RESPONSE
        if "getStreetAddons" in url:
            return _HOUSE_NUMBERS_RESPONSE
        if "getData" in url:
            return _CALENDAR_RESPONSE
        raise AssertionError(f"Unexpected URL: {url}")

    return visited_urls, fetcher


def test_source_requires_address_or_street() -> None:
    plugin = FfbWasteCollectionSourcePlugin(now_provider=lambda: date(2024, 5, 1))

    with pytest.raises(ValueError, match="address"):
        plugin.fetch({})


def test_source_resolves_eichenau_address_and_filters_requested_waste_type() -> None:
    visited_urls, fetcher = _make_json_fetcher()
    plugin = FfbWasteCollectionSourcePlugin(
        json_fetcher=fetcher,
        now_provider=lambda: date(2024, 5, 1),
    )

    result = plugin.fetch({"address": "Ringstr. 12", "waste_type": "bio"})

    assert any("client=ffb" in url for url in visited_urls)
    assert any("getStreetAddons" in url for url in visited_urls)
    assert result.address_label == "Ringstr. 12, Eichenau"
    assert result.reference_date == date(2024, 5, 1)
    assert result.entries == (
        WasteCollectionEntry(date=date(2024, 5, 2), waste_type="Biotonne"),
    )


def test_source_accepts_explicit_street_and_house_number() -> None:
    plugin = FfbWasteCollectionSourcePlugin(
        json_fetcher=_make_json_fetcher()[1],
        now_provider=lambda: date(2024, 5, 1),
    )

    result = plugin.fetch(
        {
            "street": "Ringstr.",
            "house_number": "12",
            "waste_types": ["restmuell", "papier"],
        }
    )

    assert result.entries == (
        WasteCollectionEntry(date=date(2024, 5, 1), waste_type="Restmülltonne"),
        WasteCollectionEntry(date=date(2024, 5, 5), waste_type="Papiertonne"),
    )


def test_source_maps_transient_lookup_failures_to_source_unavailable() -> None:
    def failing_fetcher(url: str):
        raise URLError("network down")

    plugin = FfbWasteCollectionSourcePlugin(
        json_fetcher=failing_fetcher,
        now_provider=lambda: date(2024, 5, 1),
    )

    with pytest.raises(SourceUnavailableError, match="ffb_waste_collection source unavailable"):
        plugin.fetch({"address": "Ringstr. 12"})


def test_source_skips_holiday_entries_with_null_fr() -> None:
    """Calendar items from AWIDO for public holidays have fr=null; they must be skipped."""

    def fetcher(url: str):
        if "getPlaces" in url:
            return _PLACES_RESPONSE
        if "getGroupedStreets" in url:
            return _STREETS_RESPONSE
        if "getStreetAddons" in url:
            return _HOUSE_NUMBERS_RESPONSE
        if "getData" in url:
            return _CALENDAR_RESPONSE_WITH_HOLIDAY
        raise AssertionError(f"Unexpected URL: {url}")

    plugin = FfbWasteCollectionSourcePlugin(
        json_fetcher=fetcher,
        now_provider=lambda: date(2024, 5, 1),
    )

    result = plugin.fetch({"address": "Ringstr. 12"})

    assert result.entries == (
        WasteCollectionEntry(date=date(2024, 5, 1), waste_type="Restmülltonne"),
        WasteCollectionEntry(date=date(2024, 5, 3), waste_type="Biotonne"),
    )
