"""Tests for the google_calendar_text renderer."""
from __future__ import annotations

from datetime import datetime, timezone
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


def _timed_event(title: str, hour: int, minute: int = 0) -> GoogleCalendarEvent:
    dt = datetime(2026, 4, 29, hour, minute, tzinfo=ZoneInfo("Europe/Berlin"))
    return GoogleCalendarEvent(title=title, start_time=dt, end_time=None, all_day=False)


def _allday_event(title: str) -> GoogleCalendarEvent:
    return GoogleCalendarEvent(title=title, start_time=None, end_time=None, all_day=True)


# ---------------------------------------------------------------------------
# Basic rendering
# ---------------------------------------------------------------------------

def test_renderer_returns_single_dashboard_text_block() -> None:
    renderer = GoogleCalendarTextRenderer()
    data = GoogleCalendarEvents(events=(_allday_event("Team standup"),))
    result = renderer.render(data, _panel())
    assert len(result) == 1
    assert isinstance(result[0], DashboardTextBlock)


def test_renderer_slot_matches_panel_slot() -> None:
    renderer = GoogleCalendarTextRenderer()
    data = GoogleCalendarEvents(events=(_allday_event("Meeting"),))
    result = renderer.render(data, _panel())
    assert result[0].slot == "gcal_events"


def test_renderer_formats_all_day_event_with_bullet() -> None:
    renderer = GoogleCalendarTextRenderer()
    data = GoogleCalendarEvents(events=(_allday_event("Conference"),))
    lines = renderer.render(data, _panel())[0].lines
    assert len(lines) == 1
    assert lines[0] == "• Conference"


def test_renderer_formats_timed_event_with_hhmm_prefix() -> None:
    renderer = GoogleCalendarTextRenderer()
    data = GoogleCalendarEvents(events=(_timed_event("Morning call", hour=9, minute=30),))
    lines = renderer.render(data, _panel())[0].lines
    assert len(lines) == 1
    assert lines[0] == "09:30 Morning call"


def test_renderer_empty_events_shows_no_events() -> None:
    renderer = GoogleCalendarTextRenderer()
    data = GoogleCalendarEvents(events=())
    lines = renderer.render(data, _panel())[0].lines
    assert len(lines) == 1
    assert lines[0] == "No events"


def test_renderer_renders_up_to_eight_events() -> None:
    renderer = GoogleCalendarTextRenderer()
    events = tuple(_timed_event(f"Event {i}", hour=i + 6) for i in range(8))
    data = GoogleCalendarEvents(events=events)
    lines = renderer.render(data, _panel())[0].lines
    assert len(lines) == 8


# ---------------------------------------------------------------------------
# Text attribute forwarding
# ---------------------------------------------------------------------------

def test_renderer_forwards_font_size_attribute() -> None:
    renderer = GoogleCalendarTextRenderer()
    data = GoogleCalendarEvents(events=(_allday_event("Meeting"),))
    result = renderer.render(data, _panel(**{"font-size": "16"}))[0]
    assert result.attributes.get("font-size") == "16"


def test_renderer_does_not_forward_unknown_attributes() -> None:
    renderer = GoogleCalendarTextRenderer()
    data = GoogleCalendarEvents(events=(_allday_event("Meeting"),))
    result = renderer.render(data, _panel(**{"unknown-key": "value"}))[0]
    assert "unknown-key" not in result.attributes


def test_renderer_supported_type_is_google_calendar_events() -> None:
    renderer = GoogleCalendarTextRenderer()
    assert renderer.supported_type is GoogleCalendarEvents
