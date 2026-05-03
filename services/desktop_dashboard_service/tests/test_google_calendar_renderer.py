"""Tests for the google_calendar_text renderer."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from epaper_dashboard_service.adapters.rendering.gcal import (
    GoogleCalendarTextRenderer,
    ProportionalEventAllocationStrategy,
    _build_day_sections,
    _sections_to_display_rows,
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
            _timed_event("Last day", reference_date + timedelta(days=3), 9),
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


def test_sections_to_display_rows_marks_day_first_and_appends_overflow_marker() -> None:
    """_sections_to_display_rows emits one row per visible event, sets day_first
    on the opening event of each day, and appends '...' to the last visible
    event when the allocator hid some entries."""
    reference_date = date(2026, 5, 4)  # Monday
    tuesday = reference_date + timedelta(days=1)
    monday_events = tuple(
        _timed_event(f"Mo-{i}", reference_date, 9 + i) for i in range(3)
    )
    tuesday_events = tuple(
        _timed_event(f"Tu-{i}", tuesday, 10 + i) for i in range(2)
    )
    data = GoogleCalendarEvents(
        reference_date=reference_date,
        display_days=2,
        events=monday_events + tuesday_events,
    )
    # Inject hidden_count=2 on Monday by capping capacity at 3 total
    sections = _build_day_sections(
        data,
        day_count=2,
        total_capacity=3,
        soft_day_limit=10,
        allocation_strategy=ProportionalEventAllocationStrategy(),
    )

    rows = _sections_to_display_rows(sections)

    # Proportional allocation: Monday 3/5 × 3 = 1.8 → 2, Tuesday 2/5 × 3 = 1.2 → 1
    # Monday has 2 visible + 1 hidden; Tuesday has 1 visible + 1 hidden
    assert len(rows) == 3
    assert rows[0].day_first is True
    assert rows[0].day == reference_date
    assert "..." not in rows[0].event_text  # first Monday event, not the last
    assert rows[1].day_first is False
    assert rows[1].day == reference_date
    assert "..." in rows[1].event_text   # last visible Monday event carries overflow marker
    assert rows[2].day_first is True
    assert rows[2].day == tuesday


def test_renderer_shows_overflow_indicator_when_total_exceeds_capacity() -> None:
    """When total events exceed max-total-events the allocator truncates and the
    last visible event for the overflowing day gets '...' appended in the image."""
    renderer = GoogleCalendarTextRenderer()
    reference_date = date(2026, 5, 4)
    # 9+2+3=14 events, capacity=8 forces truncation
    sunday_events = tuple(
        _timed_event(f"Sun-{i}", reference_date, 8 + (i % 10)) for i in range(9)
    )
    monday_events = tuple(
        _timed_event(f"Mon-{i}", reference_date + timedelta(days=1), 9 + i) for i in range(2)
    )
    tuesday_events = tuple(
        _timed_event(f"Tue-{i}", reference_date + timedelta(days=2), 10 + i) for i in range(3)
    )
    data = GoogleCalendarEvents(
        reference_date=reference_date,
        display_days=3,
        events=sunday_events + monday_events + tuesday_events,
    )

    result = renderer.render(
        data,
        _panel(**{"font-size": "14", "max-total-events": "8", "soft-day-limit": "5"}),
    )

    pixels = list(result[0].image.getdata())
    assert any(pixel < 200 for pixel in pixels)


def test_renderer_shows_all_events_when_total_fits_capacity() -> None:
    """9+2+3=14 events with max-total-events=16: all 14 must appear (no draw clipping)."""
    renderer = GoogleCalendarTextRenderer()
    reference_date = date(2026, 5, 4)
    sunday_events = tuple(
        _timed_event(f"Sun-{i}", reference_date, 8 + (i % 10)) for i in range(9)
    )
    monday_events = tuple(
        _timed_event(f"Mon-{i}", reference_date + timedelta(days=1), 9 + i) for i in range(2)
    )
    tuesday_events = tuple(
        _timed_event(f"Tue-{i}", reference_date + timedelta(days=2), 10 + i) for i in range(3)
    )
    data = GoogleCalendarEvents(
        reference_date=reference_date,
        display_days=3,
        events=sunday_events + monday_events + tuesday_events,
    )
    sections = _build_day_sections(
        data,
        day_count=3,
        total_capacity=16,
        soft_day_limit=5,
        allocation_strategy=ProportionalEventAllocationStrategy(),
    )

    rows = _sections_to_display_rows(sections)

    # Allocator grants all 14 (14 ≤ 16); no hidden_count; no overflow markers
    assert len(rows) == 14
    assert all("..." not in row.event_text for row in rows)


def test_renderer_supported_type_is_google_calendar_events() -> None:
    renderer = GoogleCalendarTextRenderer()
    assert renderer.supported_type is GoogleCalendarEvents
