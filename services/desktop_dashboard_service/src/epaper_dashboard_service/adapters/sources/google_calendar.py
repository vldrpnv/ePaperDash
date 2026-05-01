"""Google Calendar source plugin.

Fetches calendar events from an iCalendar (iCal) feed URL — for example the
"Secret address in iCal format" that Google Calendar exposes for read-only
access to a private calendar.

Configuration keys
------------------
``calendar_url`` (required)
    The iCal feed URL.  For Google Calendar this is the *Secret address in iCal
    format* found in *Settings → [calendar] → Integrate calendar*.

``timezone`` (optional, default ``"UTC"``)
    IANA timezone name used to normalise event times and to determine which
    events fall on "today".

``max_events`` (optional, default ``8``)
    Maximum number of events to return.  Events are sorted by start time
    (all-day events appear before timed events that share the same date).

``blacklist_terms`` (optional)
    Case-insensitive substrings; matching event titles are excluded.

``filter_word`` (optional)
    Single-string shorthand for one blacklist term.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from epaper_dashboard_service.domain.errors import SourceUnavailableError
from epaper_dashboard_service.domain.models import GoogleCalendarEvent, GoogleCalendarEvents
from epaper_dashboard_service.domain.ports import SourcePlugin

_LOGGER = logging.getLogger(__name__)

_DEFAULT_MAX_EVENTS = 8
_DEFAULT_TIMEZONE = "UTC"
_FETCH_TIMEOUT_SECONDS = 15


class GoogleCalendarSourcePlugin(SourcePlugin):
    """Fetch today's events from an iCal feed URL (e.g. Google Calendar secret address)."""

    name = "google_calendar"

    def fetch(self, config: dict[str, Any]) -> GoogleCalendarEvents:
        if "calendar_url" not in config:
            raise ValueError(f"{self.name} source requires config value: calendar_url")

        calendar_url = str(config["calendar_url"])
        max_events = int(config.get("max_events", _DEFAULT_MAX_EVENTS))
        timezone_name = str(config.get("timezone", _DEFAULT_TIMEZONE))
        blacklist_terms = _load_blacklist_terms(config)
        tz = _load_timezone(timezone_name)

        _LOGGER.debug(
            "GoogleCalendar fetch start url=%r timezone=%s max_events=%d blacklist_terms=%d",
            calendar_url,
            timezone_name,
            max_events,
            len(blacklist_terms),
        )

        raw_ical = _fetch_ical(calendar_url)
        today = datetime.now(tz).date()

        _LOGGER.info(
            "GoogleCalendar parsing feed date=%s timezone=%s url=%r",
            today,
            timezone_name,
            calendar_url,
        )

        try:
            events = _parse_today_events(
                raw_ical,
                today,
                tz,
                max_events,
                blacklist_terms=blacklist_terms,
            )
        except Exception as parse_error:
            raise SourceUnavailableError(
                f"{self.name} source unavailable: failed to parse iCal data"
            ) from parse_error

        _LOGGER.info("GoogleCalendar result events_today=%d date=%s", len(events), today)
        return GoogleCalendarEvents(events=tuple(events))


# ---------------------------------------------------------------------------
# iCal parsing
# ---------------------------------------------------------------------------

def _parse_today_events(
    raw_ical: bytes,
    today: date,
    tz: ZoneInfo,
    max_events: int,
    *,
    blacklist_terms: tuple[str, ...] = (),
) -> list[GoogleCalendarEvent]:
    """Parse iCal bytes and return events occurring on *today* (in *tz*)."""
    try:
        from icalendar import Calendar  # type: ignore[import-untyped]
    except ImportError as exc:
        raise SourceUnavailableError(
            "google_calendar source requires the 'icalendar' package; "
            "install it with: pip install icalendar"
        ) from exc

    cal = Calendar.from_ical(raw_ical)
    today_events: list[GoogleCalendarEvent] = []
    total_vevents = 0

    for component in cal.walk():
        if component.name != "VEVENT":
            continue

        total_vevents += 1
        today_events.extend(
            _parse_vevent(
                component,
                today,
                tz,
                blacklist_terms=blacklist_terms,
            )
        )

    _LOGGER.debug(
        "GoogleCalendar iCal walk vevents_total=%d matched_today=%d date=%s",
        total_vevents,
        len(today_events),
        today,
    )

    # Sort: all-day first (start_time is None), then by start_time ascending.
    today_events.sort(key=lambda e: (e.start_time is not None, e.start_time or datetime.min.replace(tzinfo=timezone.utc)))
    return today_events[:max_events]


def _parse_vevent(
    component: Any,
    today: date,
    tz: ZoneInfo,
    *,
    blacklist_terms: tuple[str, ...] = (),
) -> list[GoogleCalendarEvent]:
    """Return ``GoogleCalendarEvent`` values for VEVENT occurrences on *today*."""
    dtstart = component.get("DTSTART")
    dtend = component.get("DTEND")
    duration = component.get("DURATION")
    summary = str(component.get("SUMMARY", "")).strip()

    if dtstart is None:
        _LOGGER.debug("GoogleCalendar skip event=%r reason=no_dtstart", summary)
        return []

    if _title_matches_blacklist(summary, blacklist_terms):
        _LOGGER.debug("GoogleCalendar skip event=%r reason=blacklist_match", summary)
        return []

    start_dt = dtstart.dt

    # All-day event: dtstart.dt is a date, not a datetime.
    if isinstance(start_dt, date) and not isinstance(start_dt, datetime):
        duration_days = _all_day_duration_days(start_dt, dtend.dt if dtend is not None else None, duration)
        occurrences = _expand_occurrences(
            component,
            start=_normalise_all_day_datetime(start_dt),
            window_start=_normalise_all_day_datetime(today - timedelta(days=duration_days - 1)),
            window_end=_normalise_all_day_datetime(today + timedelta(days=1)),
        )
        if any(_all_day_occurrence_spans_today(occurrence, duration_days, today) for occurrence in occurrences):
            _LOGGER.debug("GoogleCalendar include all_day event=%r today=%s", summary, today)
            return [
                GoogleCalendarEvent(
                    title=summary,
                    start_time=None,
                    end_time=None,
                    all_day=True,
                )
            ]

        _LOGGER.debug("GoogleCalendar skip all_day event=%r today=%s", summary, today)
        return []

    # Timed event: normalise to target timezone.
    start_dt = _normalise_datetime(start_dt, tz)
    duration_delta = _timed_duration(start_dt, dtend.dt if dtend is not None else None, duration, tz)
    day_start = datetime.combine(today, time.min, tzinfo=tz)
    day_end = day_start + timedelta(days=1)
    search_start = day_start - max(duration_delta, timedelta())
    occurrences = _expand_occurrences(
        component,
        start=start_dt,
        window_start=search_start,
        window_end=day_end,
    )

    matching_events = [
        GoogleCalendarEvent(
            title=summary,
            start_time=occurrence,
            end_time=occurrence + duration_delta if duration_delta > timedelta() else None,
            all_day=False,
        )
        for occurrence in occurrences
        if _timed_occurrence_overlaps_day(occurrence, duration_delta, day_start, day_end)
    ]
    if matching_events:
        _LOGGER.debug("GoogleCalendar include timed event=%r count=%d", summary, len(matching_events))
    else:
        _LOGGER.debug("GoogleCalendar skip timed event=%r today=%s", summary, today)
    return matching_events


def _allday_spans_today(start: date, end: date | None, today: date) -> bool:
    """Return True if the all-day event [start, end) includes *today*.

    Google Calendar uses exclusive end dates for multi-day all-day events,
    so a single-day event on 2026-04-29 has start=2026-04-29, end=2026-04-30.
    """
    if end is None:
        return start == today
    return start <= today < end


def _load_blacklist_terms(config: dict[str, Any]) -> tuple[str, ...]:
    blacklist_terms = config.get("blacklist_terms", ())
    filter_word = config.get("filter_word")

    candidates: list[str] = []
    if isinstance(blacklist_terms, str):
        candidates.append(blacklist_terms)
    else:
        candidates.extend(str(term) for term in blacklist_terms)
    if filter_word is not None:
        candidates.append(str(filter_word))

    normalised: list[str] = []
    for candidate in candidates:
        term = candidate.strip().casefold()
        if term and term not in normalised:
            normalised.append(term)
    return tuple(normalised)


def _title_matches_blacklist(title: str, blacklist_terms: tuple[str, ...]) -> bool:
    normalised_title = title.casefold()
    return any(term in normalised_title for term in blacklist_terms)


def _normalise_datetime(value: datetime, tz: ZoneInfo) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=tz)
    return value.astimezone(tz)


def _normalise_all_day_datetime(value: date) -> datetime:
    return datetime.combine(value, time.min)


def _all_day_duration_days(
    start: date,
    end: date | None,
    duration: Any,
) -> int:
    if end is not None:
        return max((end - start).days, 1)
    if isinstance(duration, timedelta):
        return max(duration.days, 1)
    return 1


def _timed_duration(
    start: datetime,
    end: datetime | None,
    duration: Any,
    tz: ZoneInfo,
) -> timedelta:
    if isinstance(end, datetime):
        normalised_end = _normalise_datetime(end, tz)
        return max(normalised_end - start, timedelta())
    if isinstance(duration, timedelta):
        return max(duration, timedelta())
    return timedelta()


def _expand_occurrences(
    component: Any,
    *,
    start: datetime,
    window_start: datetime,
    window_end: datetime,
) -> list[datetime]:
    try:
        from dateutil.rrule import rruleset, rrulestr
    except ImportError as exc:
        raise SourceUnavailableError(
            "google_calendar source requires the 'python-dateutil' package"
        ) from exc

    recurrence_set = rruleset()
    recurrence_set.rdate(start)

    for rrule in _component_values(component, "RRULE"):
        recurrence_set.rrule(rrulestr(rrule.to_ical().decode(), dtstart=start))

    for rdate in _component_values(component, "RDATE"):
        for occurrence in _list_occurrence_values(rdate):
            recurrence_set.rdate(_coerce_occurrence_datetime(occurrence, start))

    for exdate in _component_values(component, "EXDATE"):
        for occurrence in _list_occurrence_values(exdate):
            recurrence_set.exdate(_coerce_occurrence_datetime(occurrence, start))

    return list(recurrence_set.between(window_start, window_end, inc=True))


def _component_values(component: Any, key: str) -> tuple[Any, ...]:
    values = component.get(key, [])
    if values is None:
        return ()
    if isinstance(values, list):
        return tuple(values)
    return (values,)


def _list_occurrence_values(value: Any) -> tuple[date | datetime, ...]:
    dts = getattr(value, "dts", ())
    return tuple(dt_value.dt for dt_value in dts)


def _coerce_occurrence_datetime(value: date | datetime, start: datetime) -> datetime:
    if isinstance(value, datetime):
        if start.tzinfo is None:
            return value.replace(tzinfo=None)
        if value.tzinfo is None:
            return value.replace(tzinfo=start.tzinfo)
        return value.astimezone(start.tzinfo)
    if start.tzinfo is not None:
        return datetime.combine(value, time.min, tzinfo=start.tzinfo)
    return datetime.combine(value, time.min)


def _all_day_occurrence_spans_today(occurrence: datetime, duration_days: int, today: date) -> bool:
    occurrence_date = occurrence.date()
    return _allday_spans_today(occurrence_date, occurrence_date + timedelta(days=duration_days), today)


def _timed_occurrence_overlaps_day(
    occurrence: datetime,
    duration: timedelta,
    day_start: datetime,
    day_end: datetime,
) -> bool:
    if duration == timedelta():
        return day_start <= occurrence < day_end
    return occurrence < day_end and occurrence + duration > day_start


# ---------------------------------------------------------------------------
# Network helpers
# ---------------------------------------------------------------------------

def _fetch_ical(url: str) -> bytes:
    """Fetch raw iCal bytes from *url*, raising ``SourceUnavailableError`` on failure."""
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; ePaperDash/1.0)"})
    try:
        with urlopen(req, timeout=_FETCH_TIMEOUT_SECONDS) as response:
            _LOGGER.debug("GoogleCalendar HTTP status=%s url=%s", getattr(response, "status", "?"), url)
            return response.read()
    except HTTPError as error:
        _LOGGER.error("GoogleCalendar HTTPError url=%s status=%s", url, error.code)
        raise SourceUnavailableError("google_calendar source unavailable") from error
    except URLError as error:
        _LOGGER.error("GoogleCalendar URLError url=%s reason=%s", url, error.reason)
        raise SourceUnavailableError("google_calendar source unavailable") from error
    except TimeoutError as error:
        _LOGGER.error("GoogleCalendar Timeout url=%s", url)
        raise SourceUnavailableError("google_calendar source unavailable") from error
    except OSError as error:
        _LOGGER.error("GoogleCalendar OSError url=%s reason=%s", url, error)
        raise SourceUnavailableError("google_calendar source unavailable") from error


def _load_timezone(timezone_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as error:
        raise ValueError(
            f"Invalid timezone for {GoogleCalendarSourcePlugin.name}: {timezone_name!r}"
        ) from error
