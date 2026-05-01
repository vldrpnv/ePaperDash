from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Callable, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from epaper_dashboard_service.domain.errors import SourceUnavailableError
from epaper_dashboard_service.domain.models import WasteCollectionEntry, WasteCollectionSchedule
from epaper_dashboard_service.domain.ports import SourcePlugin

_BASE_URL = "https://awido.cubefour.de/"
_CUSTOMER = "ffb"
_DEFAULT_CITY = "Eichenau"
_DEFAULT_TIMEZONE = "Europe/Berlin"
_DEFAULT_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; ePaperDash/1.0)",
}


class JsonFetcher(Protocol):
    def __call__(self, url: str) -> Any: ...


class FfbWasteCollectionSourcePlugin(SourcePlugin):
    name = "ffb_waste_collection"

    def __init__(
        self,
        json_fetcher: JsonFetcher | None = None,
        now_provider: Callable[[], date | datetime] | None = None,
    ) -> None:
        self._json_fetcher = json_fetcher or _fetch_json
        self._now_provider = now_provider or date.today

    def fetch(self, config: dict[str, Any]) -> WasteCollectionSchedule:
        city = str(config.get("city", _DEFAULT_CITY)).strip()
        timezone = _load_timezone(str(config.get("timezone", _DEFAULT_TIMEZONE)))
        street, house_number = _parse_address_config(config)
        waste_type_filters = _parse_waste_type_filters(config)
        reference_date = _reference_date(self._now_provider(), timezone)
        base_url = str(config.get("base_url", _BASE_URL))

        try:
            place_key = self._lookup_place(city, base_url)
            street_key = self._lookup_street(place_key, street, base_url)
            address_key = self._lookup_house_number(street_key, house_number, base_url) if house_number else street_key
            entries = self._fetch_entries(address_key, reference_date, waste_type_filters, base_url)
        except (URLError, TimeoutError, OSError, json.JSONDecodeError, KeyError, TypeError, IndexError) as error:
            raise SourceUnavailableError("ffb_waste_collection source unavailable") from error

        address_label = f"{street} {house_number}".strip() if house_number else street
        return WasteCollectionSchedule(
            address_label=f"{address_label}, {city}",
            reference_date=reference_date,
            entries=entries,
        )

    def _lookup_place(self, city: str, base_url: str) -> str:
        data = self._json_fetcher(_service_url(base_url, f"WebServices/Awido.Service.svc/secure/getPlaces/client={_CUSTOMER}"))
        values = {_normalize_selector(item["value"]): str(item["key"]) for item in data}
        normalized_city = _normalize_selector(city)
        if normalized_city not in values:
            raise ValueError(f"Unknown FFB waste city: {city!r}")
        return values[normalized_city]

    def _lookup_street(self, place_key: str, street: str, base_url: str) -> str:
        data = self._json_fetcher(
            _service_url(
                base_url,
                f"WebServices/Awido.Service.svc/secure/getGroupedStreets/{place_key}",
                client=_CUSTOMER,
            )
        )
        values = {_normalize_selector(item["value"]): str(item["key"]) for item in data}
        normalized_street = _normalize_selector(street)
        if normalized_street not in values:
            raise ValueError(f"Unknown FFB waste street: {street!r}")
        return values[normalized_street]

    def _lookup_house_number(self, street_key: str, house_number: str, base_url: str) -> str:
        data = self._json_fetcher(
            _service_url(
                base_url,
                f"WebServices/Awido.Service.svc/secure/getStreetAddons/{street_key}",
                client=_CUSTOMER,
            )
        )
        values = {
            _normalize_selector(item["value"]): str(item["key"])
            for item in data
            if str(item.get("value", "")).strip()
        }
        if not values:
            return street_key

        normalized_house_number = _normalize_selector(house_number)
        if normalized_house_number not in values:
            raise ValueError(f"Unknown FFB waste house number: {house_number!r}")
        return values[normalized_house_number]

    def _fetch_entries(
        self,
        address_key: str,
        reference_date: date,
        waste_type_filters: tuple[str, ...],
        base_url: str,
    ) -> tuple[WasteCollectionEntry, ...]:
        data = self._json_fetcher(
            _service_url(
                base_url,
                f"WebServices/Awido.Service.svc/secure/getData/{address_key}",
                client=_CUSTOMER,
                fractions="",
            )
        )
        fraction_names = {str(item["snm"]): str(item["nm"]) for item in data.get("fracts", ())}
        entries: list[WasteCollectionEntry] = []
        seen: set[tuple[date, str]] = set()
        for calendar_item in data.get("calendar", ()):
            raw_date = calendar_item.get("dt")
            if not isinstance(raw_date, str):
                continue
            entry_date = datetime.strptime(raw_date, "%Y%m%d").date()
            if entry_date < reference_date:
                continue
            for fraction_code in calendar_item.get("fr", ()):
                waste_type = fraction_names.get(str(fraction_code))
                if waste_type is None:
                    continue
                if waste_type_filters and not _waste_type_matches(waste_type, waste_type_filters):
                    continue
                key = (entry_date, waste_type)
                if key in seen:
                    continue
                seen.add(key)
                entries.append(WasteCollectionEntry(date=entry_date, waste_type=waste_type))
        entries.sort(key=lambda item: (item.date, item.waste_type))
        return tuple(entries)


def _parse_address_config(config: dict[str, Any]) -> tuple[str, str | None]:
    address_value = config.get("address")
    street_value = config.get("street")
    house_number_value = config.get("house_number", config.get("housenumber"))

    street: str | None = None
    house_number: str | None = None

    if address_value is not None:
        street, house_number = _split_address(str(address_value))
    elif street_value is not None:
        street = str(street_value).strip()

    if house_number_value is not None:
        house_number = str(house_number_value).strip()

    if not street:
        raise ValueError("ffb_waste_collection source requires config value: address or street")
    return street, house_number or None


def _split_address(address: str) -> tuple[str, str | None]:
    trimmed = address.strip()
    if not trimmed:
        raise ValueError("ffb_waste_collection source requires a non-empty address")
    parts = trimmed.rsplit(" ", 1)
    if len(parts) == 2 and any(char.isdigit() for char in parts[1]):
        return parts[0].strip(), parts[1].strip()
    return trimmed, None


def _parse_waste_type_filters(config: dict[str, Any]) -> tuple[str, ...]:
    raw_values = config.get("waste_types", config.get("waste_type"))
    if raw_values is None:
        return ()
    if isinstance(raw_values, str):
        values = [raw_values]
    else:
        values = list(raw_values)
    return tuple(_normalize_selector(str(value)) for value in values if str(value).strip())


def _waste_type_matches(waste_type: str, filters: tuple[str, ...]) -> bool:
    normalized_waste_type = _normalize_selector(waste_type)
    for waste_filter in filters:
        if normalized_waste_type == waste_filter:
            return True
        if normalized_waste_type.startswith(waste_filter):
            return True
    return False


def _normalize_selector(value: str) -> str:
    normalized = value.strip().lower()
    return (
        normalized.replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )


def _reference_date(value: date | datetime, timezone: ZoneInfo) -> date:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone)
        return value.astimezone(timezone).date()
    return value


def _service_url(base_url: str, path: str, **params: str) -> str:
    url = urljoin(base_url, path)
    if not params:
        return url
    return f"{url}?{urlencode(params)}"


def _load_timezone(timezone_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as error:
        raise ValueError(f"Invalid timezone for ffb_waste_collection: {timezone_name!r}") from error


def _fetch_json(url: str) -> Any:
    req = Request(url, headers=_DEFAULT_HEADERS)
    try:
        with urlopen(req, timeout=10) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
        raise SourceUnavailableError("ffb_waste_collection source unavailable") from error
