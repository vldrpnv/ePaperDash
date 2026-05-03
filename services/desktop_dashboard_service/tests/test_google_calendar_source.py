"""Tests for the google_calendar source plugin."""
from __future__ import annotations

from datetime import date, datetime, timezone
from urllib.error import URLError
from zoneinfo import ZoneInfo

import pytest

from epaper_dashboard_service.adapters.sources.google_calendar import (
    GoogleCalendarSourcePlugin,
    _allday_spans_today,
    _load_blacklist_terms,
    _parse_today_events,
    _parse_window_events,
)
from epaper_dashboard_service.domain.errors import SourceUnavailableError
from epaper_dashboard_service.domain.models import GoogleCalendarEvent, GoogleCalendarEvents


# ---------------------------------------------------------------------------
# Minimal iCal fixtures
# ---------------------------------------------------------------------------

_BERLIN = ZoneInfo("Europe/Berlin")
_TODAY = date(2026, 4, 29)

_ICAL_ONE_ALLDAY = b"""\
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
SUMMARY:Team standup
DTSTART;VALUE=DATE:20260429
DTEND;VALUE=DATE:20260430
END:VEVENT
END:VCALENDAR
"""

_ICAL_ONE_TIMED = b"""\
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
SUMMARY:Morning call
DTSTART:20260429T090000Z
DTEND:20260429T100000Z
END:VEVENT
END:VCALENDAR
"""

_ICAL_MULTI_DAY_ALLDAY = b"""\
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
SUMMARY:Conference
DTSTART;VALUE=DATE:20260428
DTEND;VALUE=DATE:20260501
END:VEVENT
END:VCALENDAR
"""

_ICAL_NO_TODAY = b"""\
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
SUMMARY:Yesterday's meeting
DTSTART:20260428T090000Z
DTEND:20260428T100000Z
END:VEVENT
END:VCALENDAR
"""

_ICAL_EIGHT_EVENTS = b"""\
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
SUMMARY:Event 1
DTSTART:20260429T060000Z
DTEND:20260429T070000Z
END:VEVENT
BEGIN:VEVENT
SUMMARY:Event 2
DTSTART:20260429T070000Z
DTEND:20260429T080000Z
END:VEVENT
BEGIN:VEVENT
SUMMARY:Event 3
DTSTART:20260429T080000Z
DTEND:20260429T090000Z
END:VEVENT
BEGIN:VEVENT
SUMMARY:Event 4
DTSTART:20260429T090000Z
DTEND:20260429T100000Z
END:VEVENT
BEGIN:VEVENT
SUMMARY:Event 5
DTSTART:20260429T100000Z
DTEND:20260429T110000Z
END:VEVENT
BEGIN:VEVENT
SUMMARY:Event 6
DTSTART:20260429T110000Z
DTEND:20260429T120000Z
END:VEVENT
BEGIN:VEVENT
SUMMARY:Event 7
DTSTART:20260429T120000Z
DTEND:20260429T130000Z
END:VEVENT
BEGIN:VEVENT
SUMMARY:Event 8
DTSTART:20260429T130000Z
DTEND:20260429T140000Z
END:VEVENT
BEGIN:VEVENT
SUMMARY:Event 9
DTSTART:20260429T140000Z
DTEND:20260429T150000Z
END:VEVENT
END:VCALENDAR
"""

_ICAL_THREE_DAY_WINDOW = b"""\
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
SUMMARY:Today event
DTSTART:20260429T090000Z
DTEND:20260429T100000Z
END:VEVENT
BEGIN:VEVENT
SUMMARY:Tomorrow event
DTSTART:20260430T090000Z
DTEND:20260430T100000Z
END:VEVENT
BEGIN:VEVENT
SUMMARY:Day after event
DTSTART:20260501T090000Z
DTEND:20260501T100000Z
END:VEVENT
END:VCALENDAR
"""


# ---------------------------------------------------------------------------
# _allday_spans_today helper
# ---------------------------------------------------------------------------

def test_allday_spans_today_single_day_matches() -> None:
    assert _allday_spans_today(date(2026, 4, 29), date(2026, 4, 30), date(2026, 4, 29))


def test_allday_spans_today_single_day_no_match() -> None:
    assert not _allday_spans_today(date(2026, 4, 28), date(2026, 4, 29), date(2026, 4, 29))


def test_allday_spans_today_multi_day_includes_today() -> None:
    assert _allday_spans_today(date(2026, 4, 27), date(2026, 5, 2), date(2026, 4, 29))


def test_allday_spans_today_no_end_date_exact_match() -> None:
    assert _allday_spans_today(date(2026, 4, 29), None, date(2026, 4, 29))


def test_allday_spans_today_no_end_date_no_match() -> None:
    assert not _allday_spans_today(date(2026, 4, 28), None, date(2026, 4, 29))


# ---------------------------------------------------------------------------
# _parse_today_events
# ---------------------------------------------------------------------------

def test_parse_today_events_all_day() -> None:
    events = _parse_today_events(_ICAL_ONE_ALLDAY, _TODAY, ZoneInfo("UTC"), max_events=8)
    assert len(events) == 1
    e = events[0]
    assert e.title == "Team standup"
    assert e.event_date == _TODAY
    assert e.all_day is True
    assert e.start_time is None
    assert e.end_time is None


def test_parse_today_events_timed_utc() -> None:
    events = _parse_today_events(_ICAL_ONE_TIMED, _TODAY, ZoneInfo("UTC"), max_events=8)
    assert len(events) == 1
    e = events[0]
    assert e.title == "Morning call"
    assert e.event_date == _TODAY
    assert e.all_day is False
    assert e.start_time is not None
    assert e.start_time.hour == 9
    assert e.start_time.tzinfo is not None


def test_parse_today_events_timed_normalised_to_berlin() -> None:
    events = _parse_today_events(_ICAL_ONE_TIMED, _TODAY, _BERLIN, max_events=8)
    assert len(events) == 1
    e = events[0]
    # 09:00 UTC → 11:00 CEST (UTC+2)
    assert e.start_time is not None
    assert e.start_time.hour == 11


def test_parse_today_events_multi_day_all_day_included() -> None:
    events = _parse_today_events(_ICAL_MULTI_DAY_ALLDAY, _TODAY, ZoneInfo("UTC"), max_events=8)
    assert len(events) == 1
    assert events[0].title == "Conference"
    assert events[0].event_date == _TODAY
    assert events[0].all_day is True


def test_parse_today_events_no_today_returns_empty() -> None:
    events = _parse_today_events(_ICAL_NO_TODAY, _TODAY, ZoneInfo("UTC"), max_events=8)
    assert events == []


def test_parse_today_events_respects_max_events() -> None:
    events = _parse_today_events(_ICAL_EIGHT_EVENTS, _TODAY, ZoneInfo("UTC"), max_events=8)
    assert len(events) == 8


def test_parse_today_events_all_day_sorted_before_timed() -> None:
    ical = b"""\
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
SUMMARY:Timed event
DTSTART:20260429T060000Z
DTEND:20260429T070000Z
END:VEVENT
BEGIN:VEVENT
SUMMARY:All day event
DTSTART;VALUE=DATE:20260429
DTEND;VALUE=DATE:20260430
END:VEVENT
END:VCALENDAR
"""
    events = _parse_today_events(ical, _TODAY, ZoneInfo("UTC"), max_events=8)
    assert len(events) == 2
    assert events[0].all_day is True
    assert events[1].all_day is False


def test_parse_window_events_includes_today_and_next_two_days() -> None:
    events = _parse_window_events(
        _ICAL_THREE_DAY_WINDOW,
        _TODAY,
        ZoneInfo("UTC"),
        max_events=8,
        days=3,
    )
    assert [(event.title, event.event_date) for event in events] == [
        ("Today event", date(2026, 4, 29)),
        ("Tomorrow event", date(2026, 4, 30)),
        ("Day after event", date(2026, 5, 1)),
    ]


# ---------------------------------------------------------------------------
# Source plugin: config validation
# ---------------------------------------------------------------------------

def test_google_calendar_source_requires_calendar_url() -> None:
    plugin = GoogleCalendarSourcePlugin()
    with pytest.raises(ValueError, match="calendar_url"):
        plugin.fetch({})


def test_google_calendar_source_raises_on_invalid_timezone() -> None:
    plugin = GoogleCalendarSourcePlugin()
    with pytest.raises(ValueError, match="Invalid timezone"):
        plugin.fetch({"calendar_url": "http://example.com/cal.ics", "timezone": "Not/ATimezone"})


# ---------------------------------------------------------------------------
# Source plugin: network error mapping
# ---------------------------------------------------------------------------

class _FakePlugin(GoogleCalendarSourcePlugin):
    """Subclass that injects a fake fetcher for the network layer."""

    def __init__(self, raw_ical: bytes | None, error: Exception | None = None) -> None:
        super().__init__()
        self._raw_ical = raw_ical
        self._error = error

    def fetch(self, config: dict) -> GoogleCalendarEvents:
        if "calendar_url" not in config:
            raise ValueError(f"{self.name} source requires config value: calendar_url")
        if self._error is not None:
            raise SourceUnavailableError("google_calendar source unavailable") from self._error
        timezone_name = str(config.get("timezone", "UTC"))
        from epaper_dashboard_service.adapters.sources.google_calendar import (
            _load_timezone,
            _parse_today_events,
        )
        tz = _load_timezone(timezone_name)
        from datetime import datetime
        today = datetime.now(tz).date()
        max_events = int(config.get("max_events", 8))
        blacklist_terms = _load_blacklist_terms(config)
        events = _parse_today_events(
            self._raw_ical,
            today,
            tz,
            max_events,
            blacklist_terms=blacklist_terms,
        )  # type: ignore[arg-type]
        return GoogleCalendarEvents(reference_date=today, events=tuple(events))


def test_google_calendar_source_maps_url_error_to_unavailable() -> None:
    plugin = _FakePlugin(raw_ical=None, error=URLError("network down"))
    with pytest.raises(SourceUnavailableError):
        plugin.fetch({"calendar_url": "http://example.com/cal.ics"})


def test_google_calendar_source_returns_google_calendar_events_type() -> None:
    plugin = _FakePlugin(raw_ical=_ICAL_ONE_ALLDAY)
    result = plugin.fetch({"calendar_url": "http://example.com/cal.ics", "timezone": "UTC"})
    assert isinstance(result, GoogleCalendarEvents)


# ---------------------------------------------------------------------------
# Recurring events and title filtering
# ---------------------------------------------------------------------------

_ICAL_RECURRING_TIMED = b"""\
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
SUMMARY:Weekly standup
DTSTART:20260107T090000Z
DTEND:20260107T093000Z
RRULE:FREQ=WEEKLY;BYDAY=WE
END:VEVENT
END:VCALENDAR
"""

_ICAL_RECURRING_ALLDAY = b"""\
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
SUMMARY:Monthly review
DTSTART;VALUE=DATE:20260107
DTEND;VALUE=DATE:20260108
RRULE:FREQ=WEEKLY;BYDAY=WE
END:VEVENT
END:VCALENDAR
"""

_ICAL_RECURRING_TIMED_EXDATE = b"""\
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
SUMMARY:Weekly standup
DTSTART:20260107T090000Z
DTEND:20260107T093000Z
RRULE:FREQ=WEEKLY;BYDAY=WE
EXDATE:20260429T090000Z
END:VEVENT
END:VCALENDAR
"""

_ICAL_FILTERED_EVENTS = b"""\
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
SUMMARY:Focus time
DTSTART:20260429T080000Z
DTEND:20260429T083000Z
END:VEVENT
BEGIN:VEVENT
SUMMARY:Private appointment
DTSTART:20260429T090000Z
DTEND:20260429T093000Z
END:VEVENT
END:VCALENDAR
"""


def test_recurring_timed_event_occurring_today_is_included() -> None:
    events = _parse_today_events(_ICAL_RECURRING_TIMED, _TODAY, ZoneInfo("UTC"), max_events=8)
    assert len(events) == 1
    assert events[0].title == "Weekly standup"
    assert events[0].all_day is False
    assert events[0].start_time == datetime(2026, 4, 29, 9, 0, tzinfo=timezone.utc)


def test_recurring_allday_event_occurring_today_is_included() -> None:
    events = _parse_today_events(_ICAL_RECURRING_ALLDAY, _TODAY, ZoneInfo("UTC"), max_events=8)
    assert len(events) == 1
    assert events[0].title == "Monthly review"
    assert events[0].all_day is True


def test_recurring_event_exdate_removes_matching_occurrence() -> None:
    events = _parse_today_events(_ICAL_RECURRING_TIMED_EXDATE, _TODAY, ZoneInfo("UTC"), max_events=8)
    assert events == []


def test_parse_today_events_filters_blacklisted_titles_case_insensitively() -> None:
    events = _parse_today_events(
        _ICAL_FILTERED_EVENTS,
        _TODAY,
        ZoneInfo("UTC"),
        max_events=8,
        blacklist_terms=("private",),
    )
    assert [event.title for event in events] == ["Focus time"]


def test_google_calendar_source_filter_word_shorthand_filters_titles() -> None:
    blacklist_terms = _load_blacklist_terms({"filter_word": "PRIVATE"})
    events = _parse_today_events(
        _ICAL_FILTERED_EVENTS,
        _TODAY,
        ZoneInfo("UTC"),
        max_events=8,
        blacklist_terms=blacklist_terms,
    )
    assert [event.title for event in events] == ["Focus time"]


def test_load_blacklist_terms_accepts_list_and_filter_word() -> None:
    terms = _load_blacklist_terms({"blacklist_terms": ["Private", "Focus"], "filter_word": "School"})
    assert terms == ("private", "focus", "school")
