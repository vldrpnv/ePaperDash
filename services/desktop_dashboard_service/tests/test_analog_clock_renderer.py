"""Tests for the AnalogClockRenderer and supporting logic.

Covers:
- Window computation for both ``start_at_render_time`` and ``start_at_next_minute`` modes.
- Renderer output contract (returns ImagePlacement, correct dimensions, not blank).
- Label mode behaviour (range, approx, none).
- Boolean config flag parsing.
- ClockSourcePlugin return type.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from epaper_dashboard_service.adapters.rendering.clock import (
    AnalogClockRenderer,
    _compute_window,
    _minute_fraction_to_pil_angle,
    _parse_bool,
)
from epaper_dashboard_service.adapters.sources.clock import ClockSourcePlugin
from epaper_dashboard_service.domain.models import ClockData, ImagePlacement, PanelDefinition


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TZ_BERLIN = timezone(timedelta(hours=2))  # CEST for stable test data


def _dt(hour: int, minute: int, second: int = 0) -> datetime:
    """Return a timezone-aware datetime in CEST on 2026-04-27."""
    return datetime(2026, 4, 27, hour, minute, second, tzinfo=_TZ_BERLIN)


def _make_panel(**renderer_config) -> PanelDefinition:
    return PanelDefinition(
        source="clock",
        renderer="analog_clock",
        slot="analog_clock",
        source_config={},
        renderer_config={"x": 10, "y": 20, "size_px": 80, **renderer_config},
    )


# ---------------------------------------------------------------------------
# _compute_window — start_at_next_minute
# ---------------------------------------------------------------------------

def test_window_start_at_next_minute_exact_minute() -> None:
    """Render at 21:26:00 → window 21:26–21:31 (already on a whole minute)."""
    render = _dt(21, 26, 0)
    start, end = _compute_window(render, 5, "start_at_next_minute")
    assert start == _dt(21, 26, 0)
    assert end == _dt(21, 31, 0)


def test_window_start_at_next_minute_partial_second() -> None:
    """Render at 21:26:49 → window 21:27–21:32 (rounds up to next minute)."""
    render = _dt(21, 26, 49)
    start, end = _compute_window(render, 5, "start_at_next_minute")
    assert start == _dt(21, 27, 0)
    assert end == _dt(21, 32, 0)


def test_window_start_at_next_minute_one_second_past() -> None:
    """Render at 21:29:10 → window 21:30–21:35."""
    render = _dt(21, 29, 10)
    start, end = _compute_window(render, 5, "start_at_next_minute")
    assert start == _dt(21, 30, 0)
    assert end == _dt(21, 35, 0)


def test_window_start_at_next_minute_custom_duration() -> None:
    """Validity window length is configurable."""
    render = _dt(10, 0, 0)
    start, end = _compute_window(render, 10, "start_at_next_minute")
    assert end - start == timedelta(minutes=10)


def test_window_start_at_next_minute_crosses_hour_boundary() -> None:
    """Render at 21:59:30 → window 22:00–22:05 (crosses hour boundary)."""
    render = _dt(21, 59, 30)
    start, end = _compute_window(render, 5, "start_at_next_minute")
    assert start.hour == 22
    assert start.minute == 0
    assert end.hour == 22
    assert end.minute == 5


# ---------------------------------------------------------------------------
# _compute_window — start_at_render_time
# ---------------------------------------------------------------------------

def test_window_start_at_render_time_exact_minute() -> None:
    """Render at 21:26:00 → window start at 21:26:00, end at 21:31:00."""
    render = _dt(21, 26, 0)
    start, end = _compute_window(render, 5, "start_at_render_time")
    assert start == render
    assert end == render + timedelta(minutes=5)


def test_window_start_at_render_time_preserves_seconds() -> None:
    """start_at_render_time preserves the seconds component."""
    render = _dt(21, 26, 49)
    start, end = _compute_window(render, 5, "start_at_render_time")
    assert start.second == 49
    assert end.second == 49


# ---------------------------------------------------------------------------
# _minute_fraction_to_pil_angle
# ---------------------------------------------------------------------------

def test_angle_at_12_oclock() -> None:
    """Minute 0 (12 o'clock) should map to 270° in PIL convention."""
    assert _minute_fraction_to_pil_angle(0) == pytest.approx(270.0)


def test_angle_at_3_oclock() -> None:
    """Minute 15 (3 o'clock) should map to 0° in PIL convention."""
    assert _minute_fraction_to_pil_angle(15) == pytest.approx(0.0)


def test_angle_monotonically_clockwise() -> None:
    """Angles should increase (mod 360) as minutes increase from 0 to 59."""
    prev = _minute_fraction_to_pil_angle(0)
    for m in range(1, 60):
        curr = _minute_fraction_to_pil_angle(m)
        # Clockwise means angle increases (mod 360); step per minute = 6°
        assert curr == pytest.approx((prev + 6.0) % 360.0, abs=1e-6)
        prev = curr


# ---------------------------------------------------------------------------
# AnalogClockRenderer — output contract
# ---------------------------------------------------------------------------

def test_renderer_returns_image_placement() -> None:
    """Renderer must return a tuple containing one ImagePlacement."""
    renderer = AnalogClockRenderer()
    data = ClockData(render_time=_dt(21, 26, 49))
    result = renderer.render(data, _make_panel())
    assert len(result) == 1
    assert isinstance(result[0], ImagePlacement)


def test_renderer_placement_coordinates_from_config() -> None:
    """x and y in renderer_config must be reflected in the ImagePlacement."""
    renderer = AnalogClockRenderer()
    data = ClockData(render_time=_dt(10, 0, 0))
    result = renderer.render(data, _make_panel(x=42, y=99))
    assert result[0].x == 42
    assert result[0].y == 99


def test_renderer_clock_image_width_at_least_size_px() -> None:
    """Image width must be at least size_px (may be wider to fit the label)."""
    renderer = AnalogClockRenderer()
    data = ClockData(render_time=_dt(10, 0, 0))
    result = renderer.render(data, _make_panel(size_px=90))
    assert result[0].image.width >= 90


def test_renderer_clock_image_height_with_range_label() -> None:
    """Image height must be greater than size_px when a label is rendered."""
    renderer = AnalogClockRenderer()
    data = ClockData(render_time=_dt(10, 0, 0))
    result = renderer.render(data, _make_panel(size_px=80, label_mode="range"))
    assert result[0].image.height > 80


def test_renderer_clock_image_height_without_label() -> None:
    """Image height must equal size_px when label_mode is 'none'."""
    renderer = AnalogClockRenderer()
    data = ClockData(render_time=_dt(10, 0, 0))
    result = renderer.render(data, _make_panel(size_px=80, label_mode="none"))
    assert result[0].image.height == 80


def test_renderer_clock_image_width_no_label_equals_size_px() -> None:
    """With no label the image width must equal size_px exactly."""
    renderer = AnalogClockRenderer()
    data = ClockData(render_time=_dt(10, 0, 0))
    result = renderer.render(data, _make_panel(size_px=80, label_mode="none"))
    assert result[0].image.width == 80


def test_renderer_image_is_not_blank() -> None:
    """The clock image must not be pure white — at least one non-white pixel expected."""
    renderer = AnalogClockRenderer()
    data = ClockData(render_time=_dt(21, 26, 49))
    result = renderer.render(data, _make_panel())
    img = result[0].image
    pixels = list(img.getdata())
    assert any(p < 200 for p in pixels), "Clock rendered as blank white image"


# ---------------------------------------------------------------------------
# Label modes
# ---------------------------------------------------------------------------

def test_label_mode_range_produces_taller_image_than_none() -> None:
    """A 'range' label adds height compared to label_mode='none'."""
    renderer = AnalogClockRenderer()
    data = ClockData(render_time=_dt(10, 30, 0))
    no_label = renderer.render(data, _make_panel(size_px=80, label_mode="none"))[0]
    with_range = renderer.render(data, _make_panel(size_px=80, label_mode="range"))[0]
    assert with_range.image.height > no_label.image.height


def test_label_mode_approx_produces_same_height_as_range() -> None:
    """Both 'range' and 'approx' produce the same label height."""
    renderer = AnalogClockRenderer()
    data = ClockData(render_time=_dt(10, 30, 0))
    range_img = renderer.render(data, _make_panel(size_px=80, label_mode="range"))[0]
    approx_img = renderer.render(data, _make_panel(size_px=80, label_mode="approx"))[0]
    assert range_img.image.height == approx_img.image.height


def test_label_mode_none_omits_label_area() -> None:
    """Image height equals size_px when label_mode is 'none'."""
    renderer = AnalogClockRenderer()
    data = ClockData(render_time=_dt(10, 30, 0))
    result = renderer.render(data, _make_panel(size_px=80, label_mode="none"))
    assert result[0].image.height == 80


# ---------------------------------------------------------------------------
# Config flags
# ---------------------------------------------------------------------------

def test_show_tick_marks_false_does_not_raise() -> None:
    """Disabling tick marks must not raise."""
    renderer = AnalogClockRenderer()
    data = ClockData(render_time=_dt(10, 0, 0))
    result = renderer.render(data, _make_panel(show_tick_marks=False))
    assert len(result) == 1


def test_show_hour_hand_false_does_not_raise() -> None:
    """Disabling the hour hand must not raise."""
    renderer = AnalogClockRenderer()
    data = ClockData(render_time=_dt(10, 0, 0))
    result = renderer.render(data, _make_panel(show_hour_hand=False))
    assert len(result) == 1


def test_renderer_with_start_at_render_time_mode() -> None:
    """window_start_mode='start_at_render_time' must not raise and returns ImagePlacement."""
    renderer = AnalogClockRenderer()
    data = ClockData(render_time=_dt(21, 26, 49))
    result = renderer.render(
        data, _make_panel(window_start_mode="start_at_render_time")
    )
    assert isinstance(result[0], ImagePlacement)


# ---------------------------------------------------------------------------
# sector_style
# ---------------------------------------------------------------------------

def test_sector_style_outer_arc_does_not_raise() -> None:
    """sector_style='outer_arc' (default) must not raise."""
    renderer = AnalogClockRenderer()
    data = ClockData(render_time=_dt(21, 26, 49))
    result = renderer.render(data, _make_panel(sector_style="outer_arc"))
    assert isinstance(result[0], ImagePlacement)


def test_sector_style_end_hand_does_not_raise() -> None:
    """sector_style='end_hand' must not raise and must return an ImagePlacement."""
    renderer = AnalogClockRenderer()
    data = ClockData(render_time=_dt(21, 26, 49))
    result = renderer.render(data, _make_panel(sector_style="end_hand"))
    assert isinstance(result[0], ImagePlacement)


def test_sector_style_end_hand_image_has_correct_dimensions() -> None:
    """end_hand image must have the same dimensions as outer_arc for equal configs."""
    renderer = AnalogClockRenderer()
    data = ClockData(render_time=_dt(10, 0, 0))
    arc = renderer.render(data, _make_panel(size_px=80, label_mode="none", sector_style="outer_arc"))[0]
    hand = renderer.render(data, _make_panel(size_px=80, label_mode="none", sector_style="end_hand"))[0]
    assert arc.image.size == hand.image.size


def test_sector_style_end_hand_is_not_blank() -> None:
    """end_hand image must not be pure white — the hand must produce dark pixels."""
    renderer = AnalogClockRenderer()
    data = ClockData(render_time=_dt(21, 26, 49))
    result = renderer.render(data, _make_panel(size_px=80, sector_style="end_hand"))
    pixels = list(result[0].image.getdata())
    assert any(p < 200 for p in pixels), "end_hand clock rendered as blank white image"


def test_sector_style_end_hand_with_label_mode_range() -> None:
    """end_hand combined with a range label must not raise."""
    renderer = AnalogClockRenderer()
    data = ClockData(render_time=_dt(21, 26, 49))
    result = renderer.render(
        data, _make_panel(sector_style="end_hand", label_mode="range")
    )
    assert isinstance(result[0], ImagePlacement)
    assert result[0].image.height > 80  # label adds height


# ---------------------------------------------------------------------------
# _parse_bool
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "value,expected",
    [
        (True, True),
        (False, False),
        ("true", True),
        ("True", True),
        ("false", False),
        ("False", False),
        ("0", False),
        ("1", True),
        ("off", False),
        ("on", True),
        (1, True),
        (0, False),
    ],
)
def test_parse_bool(value: object, expected: bool) -> None:
    assert _parse_bool(value) is expected


# ---------------------------------------------------------------------------
# ClockSourcePlugin
# ---------------------------------------------------------------------------

def test_clock_source_returns_clock_data() -> None:
    """ClockSourcePlugin.fetch must return a ClockData instance."""
    source = ClockSourcePlugin()
    result = source.fetch({"timezone": "UTC"})
    assert isinstance(result, ClockData)


def test_clock_source_render_time_is_timezone_aware() -> None:
    """The render_time must carry timezone information."""
    source = ClockSourcePlugin()
    result = source.fetch({"timezone": "Europe/Berlin"})
    assert result.render_time.tzinfo is not None


def test_clock_source_default_timezone_is_utc() -> None:
    """When no timezone is supplied the result should be UTC-aware."""
    source = ClockSourcePlugin()
    result = source.fetch({})
    assert result.render_time.utcoffset() is not None
