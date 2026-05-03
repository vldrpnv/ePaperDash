"""Tests for the google_calendar_text renderer."""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from epaper_dashboard_service.adapters.rendering.gcal import GoogleCalendarTextRenderer
from epaper_dashboard_service.domain.models import (
    DashboardTextBlock,
    GoogleCalendarEvent,
    GoogleCalendarEvents,
    PanelDefinition,
)


def _panel(**renderer_config) -> PanelDefinition:
    return PanelDefinition(
        source="google_calendar",
        renderer="google_calendar_text",
        slot="gcal_events",
        source_config={},
        renderer_config=renderer_config,
    )


def _timed_event(
    title: str,
    event_date: date,
    hour: int,
    minute: int = 0,
) -> GoogleCalendarEvent:
    dt = datetime(event_date.year, event_date.month, event_date.day, hour, minute, tzinfo=ZoneInfo("Europe/Berlin"))
    return GoogleCalendarEvent(
        title=title,
        event_date=event_date,
        start_time=dt,
        end_time=None,
        all_day=False,
    )


def _allday_event(title: str, event_date: date) -> GoogleCalendarEvent:
    return GoogleCalendarEvent(
        title=title,
        event_date=event_date,
        start_time=None,
        end_time=None,
        all_day=True,
    )


# ---------------------------------------------------------------------------
# Basic rendering
# ---------------------------------------------------------------------------

def test_renderer_returns_three_dashboard_text_blocks() -> None:
    renderer = GoogleCalendarTextRenderer()
    data = GoogleCalendarEvents(
        reference_date=date(2026, 4, 29),
        events=(_allday_event("Team standup", date(2026, 4, 29)),),
    )
    result = renderer.render(data, _panel())
    assert len(result) == 3
    assert all(isinstance(block, DashboardTextBlock) for block in result)


def test_renderer_slots_match_day_suffixes() -> None:
    renderer = GoogleCalendarTextRenderer()
    data = GoogleCalendarEvents(
        reference_date=date(2026, 4, 29),
        events=(_allday_event("Meeting", date(2026, 4, 29)),),
    )
    result = renderer.render(data, _panel())
    assert tuple(block.slot for block in result) == (
        "gcal_events_0",
        "gcal_events_1",
        "gcal_events_2",
    )


def test_renderer_labels_today_tomorrow_and_next_day() -> None:
    renderer = GoogleCalendarTextRenderer()
    data = GoogleCalendarEvents(reference_date=date(2026, 4, 29), events=())
    result = renderer.render(data, _panel())
    assert result[0].lines[0] == "Wednesday, today"
    assert result[1].lines[0] == "Thursday, tomorrow"
    assert result[2].lines[0] == "Friday"


def test_renderer_formats_all_day_event_with_bullet() -> None:
    renderer = GoogleCalendarTextRenderer()
    data = GoogleCalendarEvents(
        reference_date=date(2026, 4, 29),
        events=(_allday_event("Conference", date(2026, 4, 29)),),
    )
    lines = renderer.render(data, _panel())[0].lines
    assert lines[1] == "• Conference"


def test_renderer_formats_timed_event_with_hhmm_prefix() -> None:
    renderer = GoogleCalendarTextRenderer()
    data = GoogleCalendarEvents(
        reference_date=date(2026, 4, 29),
        events=(_timed_event("Morning call", date(2026, 4, 29), hour=9, minute=30),),
    )
    lines = renderer.render(data, _panel())[0].lines
    assert lines[1] == "09:30 Morning call"


def test_renderer_empty_events_shows_no_events_for_each_day() -> None:
    renderer = GoogleCalendarTextRenderer()
    data = GoogleCalendarEvents(reference_date=date(2026, 4, 29), events=())
    result = renderer.render(data, _panel())
    assert all(block.lines[1] == "No events" for block in result)


def test_renderer_limits_each_day_to_five_events() -> None:
    renderer = GoogleCalendarTextRenderer()
    event_day = date(2026, 4, 29)
    events = tuple(_timed_event(f"Event {i}", event_day, hour=i + 6) for i in range(6))
    data = GoogleCalendarEvents(reference_date=event_day, events=events)
    lines = renderer.render(data, _panel())[0].lines
    assert len(lines) == 6
    assert lines[-1] == "10:00 Event 4"


# ---------------------------------------------------------------------------
# Text attribute forwarding
# ---------------------------------------------------------------------------

def test_renderer_forwards_font_size_attribute() -> None:
    renderer = GoogleCalendarTextRenderer()
    data = GoogleCalendarEvents(
        reference_date=date(2026, 4, 29),
        events=(_allday_event("Meeting", date(2026, 4, 29)),),
    )
    result = renderer.render(data, _panel(**{"font-size": "16"}))[0]
    assert result.attributes.get("font-size") == "16"


def test_renderer_does_not_forward_unknown_attributes() -> None:
    renderer = GoogleCalendarTextRenderer()
    data = GoogleCalendarEvents(
        reference_date=date(2026, 4, 29),
        events=(_allday_event("Meeting", date(2026, 4, 29)),),
    )
    result = renderer.render(data, _panel(**{"unknown-key": "value"}))[0]
    assert "unknown-key" not in result.attributes


def test_renderer_supported_type_is_google_calendar_events() -> None:
    renderer = GoogleCalendarTextRenderer()
    assert renderer.supported_type is GoogleCalendarEvents
