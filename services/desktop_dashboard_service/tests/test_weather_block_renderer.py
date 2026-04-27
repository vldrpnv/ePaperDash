"""Tests for WeatherBlockRenderer — block selection algorithm and rendering contract."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from epaper_dashboard_service.adapters.icons.null_provider import NullWeatherIconProvider
from epaper_dashboard_service.adapters.rendering.weather import (
    WeatherBlockRenderer,
    _select_weather_blocks,
)
from epaper_dashboard_service.domain.models import (
    ImagePlacement,
    PanelDefinition,
    WeatherForecast,
    WeatherPeriod,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TZ_BERLIN = timezone(timedelta(hours=2))  # CEST for test stability


def _local(date_str: str, hour: int) -> datetime:
    """Return an aware datetime in Europe/Berlin (CEST, UTC+2) for a given date and hour."""
    return datetime(
        int(date_str[:4]), int(date_str[5:7]), int(date_str[8:10]),
        hour, 0,
        tzinfo=_TZ_BERLIN,
    )


def _make_periods(
    start_date: str,
    hours: list[int],
    icon: str = "\u2600",
    label: str = "Sunny",
    temp: float = 15.0,
) -> tuple[WeatherPeriod, ...]:
    """Create one-hour WeatherPeriod objects for the given date and hours."""
    return tuple(
        WeatherPeriod(
            start_time=_local(start_date, h),
            end_time=_local(start_date, h) + timedelta(hours=1),
            temperature_c=temp + h * 0.1,
            precipitation_probability_percent=10,
            condition_label=label,
            condition_icon=icon,
            precipitation_mm=0.0,
        )
        for h in hours
    )


def _make_two_day_forecast(today: str, tomorrow: str) -> tuple[WeatherPeriod, ...]:
    """Return hourly periods covering 00:00–23:00 for today and tomorrow."""
    return _make_periods(today, list(range(24))) + _make_periods(tomorrow, list(range(24)))


def _make_panel(**renderer_config) -> PanelDefinition:
    return PanelDefinition(
        source="weather_forecast",
        renderer="weather_block",
        slot="weather_block",
        source_config={},
        renderer_config={"x": 0, "y": 190, "width": 800, "height": 170, **renderer_config},
    )


# ---------------------------------------------------------------------------
# Block selection algorithm — canonical examples from the spec
#
# Core hours: 06–22.  A today-slot is only valid if it starts at ≤ 20
# (so it ends at most at midnight).  Nightly slots (00–05) are never shown.
#
# H <= 12:             three today-slots  S1=H, S2=max(H+8,18)-4, S3=max(H+8,18)
# 13 <= H <= 16:       two today + one tomorrow  S1=H, S2=max(H+4,18), S3=(tmrw,06)
# 17 <= H <= 20:       one today + two tomorrow  S1=H, S2=(tmrw,06), S3=(tmrw,10)
# H >= 21 or H < 6:   all tomorrow  (tmrw,06), (tmrw,10), (tmrw,14)
# ---------------------------------------------------------------------------

def test_block_selection_at_06():
    """at 06:00 → H<=12: S3=max(14,18)=18, S2=14, S1=6 → 06-10, 14-18, 18-22."""
    now = _local("2026-04-27", 6)
    periods = _make_two_day_forecast("2026-04-27", "2026-04-28")
    blocks = _select_weather_blocks(periods, now)
    assert len(blocks) == 3
    assert "06" in blocks[0].time_label
    assert "tmrw" not in blocks[0].time_label
    assert "14" in blocks[1].time_label
    assert "tmrw" not in blocks[1].time_label
    assert "18" in blocks[2].time_label
    assert "tmrw" not in blocks[2].time_label


def test_block_selection_at_08():
    """at 08:00 → H<=12: S3=max(16,18)=18, S2=14, S1=8 → 08-12, 14-18, 18-22."""
    now = _local("2026-04-27", 8)
    periods = _make_two_day_forecast("2026-04-27", "2026-04-28")
    blocks = _select_weather_blocks(periods, now)
    assert len(blocks) == 3
    assert "08" in blocks[0].time_label
    assert "tmrw" not in blocks[0].time_label
    assert "14" in blocks[1].time_label
    assert "tmrw" not in blocks[1].time_label
    assert "18" in blocks[2].time_label
    assert "tmrw" not in blocks[2].time_label


def test_block_selection_at_09():
    """at 09:00 → H<=12: S3=max(17,18)=18, S2=14, S1=9 → 09-13, 14-18, 18-22."""
    now = _local("2026-04-27", 9)
    periods = _make_two_day_forecast("2026-04-27", "2026-04-28")
    blocks = _select_weather_blocks(periods, now)
    assert len(blocks) == 3
    assert "09" in blocks[0].time_label
    assert "tmrw" not in blocks[0].time_label
    assert "14" in blocks[1].time_label
    assert "tmrw" not in blocks[1].time_label
    assert "18" in blocks[2].time_label
    assert "tmrw" not in blocks[2].time_label


def test_block_selection_at_10():
    """at 10:00 → H<=12: S3=max(18,18)=18, S2=14, S1=10 → 10-14, 14-18, 18-22."""
    now = _local("2026-04-27", 10)
    periods = _make_two_day_forecast("2026-04-27", "2026-04-28")
    blocks = _select_weather_blocks(periods, now)
    assert len(blocks) == 3
    assert "10" in blocks[0].time_label
    assert "tmrw" not in blocks[0].time_label
    assert "14" in blocks[1].time_label
    assert "tmrw" not in blocks[1].time_label
    assert "18" in blocks[2].time_label
    assert "tmrw" not in blocks[2].time_label


def test_block_selection_at_11():
    """at 11:00 → H<=12: S3=max(19,18)=19, S2=15, S1=11 → 11-15, 15-19, 19-23."""
    now = _local("2026-04-27", 11)
    periods = _make_two_day_forecast("2026-04-27", "2026-04-28")
    blocks = _select_weather_blocks(periods, now)
    assert len(blocks) == 3
    assert "11" in blocks[0].time_label
    assert "tmrw" not in blocks[0].time_label
    assert "15" in blocks[1].time_label
    assert "tmrw" not in blocks[1].time_label
    assert "19" in blocks[2].time_label
    assert "tmrw" not in blocks[2].time_label


def test_block_selection_at_12():
    """at 12:00 → H<=12: S3=max(20,18)=20, S2=16, S1=12 → 12-16, 16-20, 20-00 (all today)."""
    now = _local("2026-04-27", 12)
    periods = _make_two_day_forecast("2026-04-27", "2026-04-28")
    blocks = _select_weather_blocks(periods, now)
    assert len(blocks) == 3
    assert "12" in blocks[0].time_label
    assert "tmrw" not in blocks[0].time_label
    assert "16" in blocks[1].time_label
    assert "tmrw" not in blocks[1].time_label
    assert "20" in blocks[2].time_label
    assert "tmrw" not in blocks[2].time_label


def test_block_selection_at_13():
    """at 13:00 → 13<=H<=16: S2=max(17,18)=18, S1=13, S3=tmrw 06 → 13, 18, tmrw 06."""
    now = _local("2026-04-27", 13)
    periods = _make_two_day_forecast("2026-04-27", "2026-04-28")
    blocks = _select_weather_blocks(periods, now)
    assert len(blocks) == 3
    assert "13" in blocks[0].time_label
    assert "tmrw" not in blocks[0].time_label
    assert "18" in blocks[1].time_label
    assert "tmrw" not in blocks[1].time_label
    assert "tmrw" in blocks[2].time_label
    assert "06" in blocks[2].time_label


def test_block_selection_at_14():
    """at 14:00 → 13<=H<=16: S2=max(18,18)=18, S1=14, S3=tmrw 06 → 14, 18, tmrw 06."""
    now = _local("2026-04-27", 14)
    periods = _make_two_day_forecast("2026-04-27", "2026-04-28")
    blocks = _select_weather_blocks(periods, now)
    assert len(blocks) == 3
    assert "14" in blocks[0].time_label
    assert "tmrw" not in blocks[0].time_label
    assert "18" in blocks[1].time_label
    assert "tmrw" not in blocks[1].time_label
    assert "tmrw" in blocks[2].time_label
    assert "06" in blocks[2].time_label


def test_block_selection_at_15():
    """at 15:00 → 13<=H<=16: S2=max(19,18)=19, S1=15, S3=tmrw 06 → 15, 19, tmrw 06."""
    now = _local("2026-04-27", 15)
    periods = _make_two_day_forecast("2026-04-27", "2026-04-28")
    blocks = _select_weather_blocks(periods, now)
    assert len(blocks) == 3
    assert "15" in blocks[0].time_label
    assert "tmrw" not in blocks[0].time_label
    assert "19" in blocks[1].time_label
    assert "tmrw" not in blocks[1].time_label
    assert "tmrw" in blocks[2].time_label
    assert "06" in blocks[2].time_label


def test_block_selection_at_16():
    """at 16:00 → 13<=H<=16: S2=max(20,18)=20, S1=16, S3=tmrw 06 → 16, 20, tmrw 06."""
    now = _local("2026-04-27", 16)
    periods = _make_two_day_forecast("2026-04-27", "2026-04-28")
    blocks = _select_weather_blocks(periods, now)
    assert len(blocks) == 3
    assert "16" in blocks[0].time_label
    assert "tmrw" not in blocks[0].time_label
    assert "20" in blocks[1].time_label
    assert "tmrw" not in blocks[1].time_label
    assert "tmrw" in blocks[2].time_label
    assert "06" in blocks[2].time_label


def test_block_selection_at_17():
    """at 17:00 → 17<=H<=20: S1=17 today, S2=tmrw 06, S3=tmrw 10."""
    now = _local("2026-04-27", 17)
    periods = _make_two_day_forecast("2026-04-27", "2026-04-28")
    blocks = _select_weather_blocks(periods, now)
    assert len(blocks) == 3
    assert "17" in blocks[0].time_label
    assert "tmrw" not in blocks[0].time_label
    assert "tmrw" in blocks[1].time_label
    assert "06" in blocks[1].time_label
    assert "tmrw" in blocks[2].time_label
    assert "10" in blocks[2].time_label


def test_block_selection_at_20():
    """at 20:00 → 17<=H<=20: S1=20 today (20-00), S2=tmrw 06, S3=tmrw 10."""
    now = _local("2026-04-27", 20)
    periods = _make_two_day_forecast("2026-04-27", "2026-04-28")
    blocks = _select_weather_blocks(periods, now)
    assert len(blocks) == 3
    assert "20" in blocks[0].time_label
    assert "tmrw" not in blocks[0].time_label
    assert "tmrw" in blocks[1].time_label
    assert "06" in blocks[1].time_label
    assert "tmrw" in blocks[2].time_label
    assert "10" in blocks[2].time_label


def test_block_selection_at_21():
    """at 21:00 → H>=21: all three slots are tomorrow 06, 10, 14."""
    now = _local("2026-04-27", 21)
    periods = _make_two_day_forecast("2026-04-27", "2026-04-28")
    blocks = _select_weather_blocks(periods, now)
    assert len(blocks) == 3
    assert "tmrw" in blocks[0].time_label
    assert "06" in blocks[0].time_label
    assert "tmrw" in blocks[1].time_label
    assert "10" in blocks[1].time_label
    assert "tmrw" in blocks[2].time_label
    assert "14" in blocks[2].time_label


# ---------------------------------------------------------------------------
# Renderer output contract
# ---------------------------------------------------------------------------

def test_weather_block_renderer_returns_image_placement():
    renderer = WeatherBlockRenderer(icon_provider=NullWeatherIconProvider())
    now = datetime(2026, 4, 27, 10, 0, tzinfo=_TZ_BERLIN)
    data = WeatherForecast(
        location_name="Eichenau",
        provider="open_meteo",
        source_precision_hours=1,
        periods=_make_two_day_forecast("2026-04-27", "2026-04-28"),
    )
    result = renderer.render(data, _make_panel())
    assert len(result) == 1
    assert isinstance(result[0], ImagePlacement)


def test_weather_block_renderer_image_has_correct_dimensions():
    renderer = WeatherBlockRenderer(icon_provider=NullWeatherIconProvider())
    data = WeatherForecast(
        location_name="Eichenau",
        provider="open_meteo",
        source_precision_hours=1,
        periods=_make_two_day_forecast("2026-04-27", "2026-04-28"),
    )
    result = renderer.render(data, _make_panel(width=800, height=170))
    placement = result[0]
    assert isinstance(placement, ImagePlacement)
    assert placement.image.width == 800
    assert placement.image.height == 170


def test_weather_block_renderer_placement_coordinates_from_renderer_config():
    renderer = WeatherBlockRenderer(icon_provider=NullWeatherIconProvider())
    data = WeatherForecast(
        location_name="Eichenau",
        provider="open_meteo",
        source_precision_hours=1,
        periods=_make_two_day_forecast("2026-04-27", "2026-04-28"),
    )
    result = renderer.render(data, _make_panel(x=5, y=200, width=800, height=170))
    placement = result[0]
    assert isinstance(placement, ImagePlacement)
    assert placement.x == 5
    assert placement.y == 200


def test_weather_block_renderer_works_with_empty_periods():
    """Empty forecast must not raise — produces a blank image."""
    renderer = WeatherBlockRenderer(icon_provider=NullWeatherIconProvider())
    data = WeatherForecast(
        location_name="Eichenau",
        provider="open_meteo",
        source_precision_hours=1,
        periods=(),
    )
    result = renderer.render(data, _make_panel())
    assert len(result) == 1
    assert isinstance(result[0], ImagePlacement)


# ---------------------------------------------------------------------------
# Row 1 today overview — precipitation suppression threshold
# ---------------------------------------------------------------------------

def test_block_selection_aggregate_precipitation_when_notable():
    """Precip should accumulate across the block's periods."""
    today = "2026-04-27"
    rainy = tuple(
        WeatherPeriod(
            start_time=_local(today, h),
            end_time=_local(today, h) + timedelta(hours=1),
            temperature_c=10.0,
            precipitation_probability_percent=60,
            condition_label="Rain",
            condition_icon="\u2614",
            precipitation_mm=0.5,
        )
        for h in range(6, 10)  # 4 hours
    )
    other = _make_periods(today, list(range(10, 24)))
    tomorrow_periods = _make_periods("2026-04-28", list(range(24)))
    now = _local(today, 6)
    blocks = _select_weather_blocks(rainy + other + tomorrow_periods, now)
    # First block covers 06-10 — should sum 4 × 0.5 = 2.0 mm
    first = blocks[0]
    assert first.precipitation_mm == pytest.approx(2.0)
    assert first.precipitation_prob == 60


def test_block_selection_no_precip_when_below_threshold():
    """Block with low probability and 0 mm — precipitation_prob and mm both low."""
    today = "2026-04-27"
    dry_periods = _make_periods(today, list(range(24)))
    tomorrow_periods = _make_periods("2026-04-28", list(range(24)))
    now = _local(today, 6)
    blocks = _select_weather_blocks(dry_periods + tomorrow_periods, now)
    first = blocks[0]
    assert first.precipitation_prob < 40
    assert first.precipitation_mm == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# base_font_size renderer_config key
# ---------------------------------------------------------------------------

def test_weather_block_renderer_accepts_base_font_size_override():
    """Providing base_font_size in renderer_config must not raise and must return an ImagePlacement."""
    renderer = WeatherBlockRenderer(icon_provider=NullWeatherIconProvider())
    data = WeatherForecast(
        location_name="Eichenau",
        provider="open_meteo",
        source_precision_hours=1,
        periods=_make_two_day_forecast("2026-04-27", "2026-04-28"),
    )
    result = renderer.render(data, _make_panel(base_font_size=24))
    assert len(result) == 1
    assert isinstance(result[0], ImagePlacement)


def test_weather_block_renderer_base_font_size_controls_layout_fonts():
    """_compute_layout must use base_font_size as font_lg_size when provided."""
    from epaper_dashboard_service.adapters.rendering.weather import _compute_layout
    lo_default = _compute_layout(170)
    lo_custom = _compute_layout(170, base_font_size=30)
    assert lo_custom["font_lg_size"] == 30
    assert lo_custom["font_lg_size"] != lo_default["font_lg_size"]
    assert lo_custom["font_md_size"] < lo_custom["font_lg_size"]
    assert lo_custom["font_sm_size"] < lo_custom["font_md_size"]
