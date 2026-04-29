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
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
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
        tz = _load_timezone(timezone_name)

        _LOGGER.debug(
            "GoogleCalendar fetch start url=%r timezone=%s max_events=%d",
            calendar_url,
            timezone_name,
            max_events,
        )

        raw_ical = _fetch_ical(calendar_url)
        today = datetime.now(tz).date()

        try:
            events = _parse_today_events(raw_ical, today, tz, max_events)
        except Exception as parse_error:
            raise SourceUnavailableError(
                f"{self.name} source unavailable: failed to parse iCal data"
            ) from parse_error

        _LOGGER.debug("GoogleCalendar events found count=%d date=%s", len(events), today)
        return GoogleCalendarEvents(events=tuple(events))


# ---------------------------------------------------------------------------
# iCal parsing
# ---------------------------------------------------------------------------

def _parse_today_events(
    raw_ical: bytes,
    today: date,
    tz: ZoneInfo,
    max_events: int,
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

    for component in cal.walk():
        if component.name != "VEVENT":
            continue

        event = _parse_vevent(component, today, tz)
        if event is not None:
            today_events.append(event)

    # Sort: all-day first (start_time is None), then by start_time ascending.
    today_events.sort(key=lambda e: (e.start_time is not None, e.start_time or datetime.min.replace(tzinfo=timezone.utc)))
    return today_events[:max_events]


def _parse_vevent(component: Any, today: date, tz: ZoneInfo) -> GoogleCalendarEvent | None:
    """Return a ``GoogleCalendarEvent`` if the VEVENT falls on *today*, else ``None``."""
    try:
        from icalendar import vDatetime, vDate  # type: ignore[import-untyped]
    except ImportError:
        return None

    dtstart = component.get("DTSTART")
    dtend = component.get("DTEND")
    summary = str(component.get("SUMMARY", "")).strip()

    if dtstart is None:
        return None

    start_dt = dtstart.dt

    # All-day event: dtstart.dt is a date, not a datetime.
    if isinstance(start_dt, date) and not isinstance(start_dt, datetime):
        end_dt = dtend.dt if dtend is not None else None
        # All-day events span [start, end) — end is exclusive.
        if _allday_spans_today(start_dt, end_dt, today):
            return GoogleCalendarEvent(
                title=summary,
                start_time=None,
                end_time=None,
                all_day=True,
            )
        return None

    # Timed event: normalise to target timezone.
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=tz)
    else:
        start_dt = start_dt.astimezone(tz)

    if start_dt.date() != today:
        return None

    end_dt_aware: datetime | None = None
    if dtend is not None and isinstance(dtend.dt, datetime):
        end_dt_aware = dtend.dt
        if end_dt_aware.tzinfo is None:
            end_dt_aware = end_dt_aware.replace(tzinfo=tz)
        else:
            end_dt_aware = end_dt_aware.astimezone(tz)

    return GoogleCalendarEvent(
        title=summary,
        start_time=start_dt,
        end_time=end_dt_aware,
        all_day=False,
    )


def _allday_spans_today(start: date, end: date | None, today: date) -> bool:
    """Return True if the all-day event [start, end) includes *today*.

    Google Calendar uses exclusive end dates for multi-day all-day events,
    so a single-day event on 2026-04-29 has start=2026-04-29, end=2026-04-30.
    """
    if end is None:
        return start == today
    return start <= today < end


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
