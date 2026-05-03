"""Tests for the google_calendar_text renderer."""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from epaper_dashboard_service.adapters.rendering.gcal import (
    GoogleCalendarTextRenderer,
    ProportionalEventAllocationStrategy,
    _build_day_sections,
)
from epaper_dashboard_service.domain.models import (
    GoogleCalendarEvent,
    GoogleCalendarEvents,
    ImagePlacement,
    PanelDefinition,
)


def _panel(**renderer_config) -> PanelDefinition:
    return PanelDefinition(
        source="google_calendar",
        renderer="google_calendar_text",
        slot="gcal_events",
        source_config={},
        renderer_config={
            "x": 196,
            "y": 198,
            "width": 596,
            "height": 124,
            **renderer_config,
        },
    )


def _timed_event(
    title: str,
    event_date: date,
    hour: int,
    minute: int = 0,
) -> GoogleCalendarEvent:
    dt = datetime(
        event_date.year,
        event_date.month,
        event_date.day,
        hour,
        minute,
        tzinfo=ZoneInfo("Europe/Berlin"),
    )
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


def test_strategy_shows_all_events_when_total_fits() -> None:
    strategy = ProportionalEventAllocationStrategy()
    allocation = strategy.allocate((7, 2, 6), total_capacity=16, soft_day_limit=5)
    assert allocation == (7, 2, 6)


def test_strategy_caps_all_days_at_five_when_every_day_overflows() -> None:
    strategy = ProportionalEventAllocationStrategy()
    allocation = strategy.allocate((7, 8, 9), total_capacity=16, soft_day_limit=5)
    assert allocation == (5, 5, 5)


def test_strategy_rebalances_remaining_capacity_proportionally() -> None:
    strategy = ProportionalEventAllocationStrategy()
    allocation = strategy.allocate((5, 10, 20), total_capacity=16, soft_day_limit=5)
    assert allocation == (5, 4, 7)


def test_build_day_sections_uses_configurable_day_count() -> None:
    reference_date = date(2026, 5, 4)
    data = GoogleCalendarEvents(
        reference_date=reference_date,
        display_days=4,
        events=(
            _allday_event("Today", reference_date),
            _timed_event("Last day", reference_date.replace(day=7), 9),
        ),
    )
    sections = _build_day_sections(
        data,
        day_count=4,
        total_capacity=16,
        soft_day_limit=5,
        allocation_strategy=ProportionalEventAllocationStrategy(),
    )
    assert [section.label for section in sections] == [
        "Monday, today",
        "Tuesday, tomorrow",
        "Wednesday",
        "Thursday",
    ]
    assert [len(section.visible_events) for section in sections] == [1, 0, 0, 1]


def test_build_day_sections_marks_hidden_events_for_overflow_indicator() -> None:
    reference_date = date(2026, 5, 4)
    day_1 = tuple(_timed_event(f"D1-{index}", reference_date, 8 + index, index) for index in range(5))
    day_2_date = date(2026, 5, 5)
    day_2 = tuple(_timed_event(f"D2-{index}", day_2_date, 8 + (index % 10), index) for index in range(10))
    day_3_date = date(2026, 5, 6)
    day_3 = tuple(_timed_event(f"D3-{index}", day_3_date, 8 + (index % 10), index) for index in range(20))
    data = GoogleCalendarEvents(
        reference_date=reference_date,
        display_days=3,
        events=day_1 + day_2 + day_3,
    )
    sections = _build_day_sections(
        data,
        day_count=3,
        total_capacity=16,
        soft_day_limit=5,
        allocation_strategy=ProportionalEventAllocationStrategy(),
    )
    assert [len(section.visible_events) for section in sections] == [5, 4, 7]
    assert [section.hidden_count for section in sections] == [0, 6, 13]


def test_renderer_returns_single_image_placement_matching_slot_geometry() -> None:
    renderer = GoogleCalendarTextRenderer()
    reference_date = date(2026, 5, 4)
    data = GoogleCalendarEvents(
        reference_date=reference_date,
        display_days=3,
        events=(_allday_event("Team standup", reference_date),),
    )
    result = renderer.render(data, _panel())
    assert len(result) == 1
    assert isinstance(result[0], ImagePlacement)
    assert result[0].x == 196
    assert result[0].y == 198
    assert result[0].image.size == (596, 124)


def test_renderer_image_is_not_blank() -> None:
    renderer = GoogleCalendarTextRenderer()
    reference_date = date(2026, 5, 4)
    data = GoogleCalendarEvents(
        reference_date=reference_date,
        display_days=3,
        events=(
            _allday_event("Conference", reference_date),
            _timed_event("Morning call", date(2026, 5, 5), hour=9, minute=30),
        ),
    )
    result = renderer.render(data, _panel())
    pixels = list(result[0].image.getdata())
    assert any(pixel < 200 for pixel in pixels)


def test_renderer_supported_type_is_google_calendar_events() -> None:
    renderer = GoogleCalendarTextRenderer()
    assert renderer.supported_type is GoogleCalendarEvents
