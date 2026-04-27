"""Visual regression / golden-preview tests for the dashboard layout.

These tests use fixed input data and verify:
- Generated images have the expected dimensions.
- Key content regions do not overlap.
- The weather block renders correctly with real forecast data.
- The SVG layout pipeline produces a correctly sized output image.
- German long text strings and zero/low precipitation values are handled.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from epaper_dashboard_service.adapters.icons.null_provider import NullWeatherIconProvider
from epaper_dashboard_service.adapters.layout.svg import (
    SvgLayoutRenderer,
    check_slot_overlaps,
    collect_slot_bboxes,
)
from epaper_dashboard_service.adapters.rendering.weather import WeatherBlockRenderer
from epaper_dashboard_service.domain.models import (
    DashboardTextBlock,
    ImagePlacement,
    PanelDefinition,
    WeatherForecast,
    WeatherPeriod,
)


# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

_TZ_BERLIN = timezone(timedelta(hours=2))  # CEST for stable test data

_DASHBOARD_WIDTH = 800
_DASHBOARD_HEIGHT = 480
_WEATHER_BLOCK_X = 305
_WEATHER_BLOCK_Y = 163
_WEATHER_BLOCK_W = 490
_WEATHER_BLOCK_H = 312


def _local(date_str: str, hour: int) -> datetime:
    return datetime(
        int(date_str[:4]), int(date_str[5:7]), int(date_str[8:10]),
        hour, 0,
        tzinfo=_TZ_BERLIN,
    )


def _make_period(
    date_str: str,
    hour: int,
    temp: float = 18.0,
    precip_prob: int = 10,
    precip_mm: float = 0.0,
    icon: str = "\u2600",
    label: str = "Sunny",
) -> WeatherPeriod:
    start = _local(date_str, hour)
    return WeatherPeriod(
        start_time=start,
        end_time=start + timedelta(hours=1),
        temperature_c=temp,
        precipitation_probability_percent=precip_prob,
        condition_label=label,
        condition_icon=icon,
        precipitation_mm=precip_mm,
    )


def _make_forecast(today: str = "2026-04-27", tomorrow: str = "2026-04-28") -> WeatherForecast:
    """Return a two-day hourly forecast with varied conditions."""
    today_periods = tuple(
        _make_period(today, h, temp=10.0 + h * 0.5, precip_prob=5 if h < 12 else 20)
        for h in range(24)
    )
    tomorrow_periods = tuple(
        _make_period(tomorrow, h, temp=12.0 + h * 0.3, precip_prob=30, precip_mm=0.2)
        for h in range(24)
    )
    return WeatherForecast(
        location_name="Eichenau",
        provider="open_meteo",
        source_precision_hours=1,
        periods=today_periods + tomorrow_periods,
    )


def _make_weather_panel(**extra) -> PanelDefinition:
    return PanelDefinition(
        source="weather_forecast",
        renderer="weather_block",
        slot="weather_block",
        source_config={},
        renderer_config={
            "x": _WEATHER_BLOCK_X,
            "y": _WEATHER_BLOCK_Y,
            "width": _WEATHER_BLOCK_W,
            "height": _WEATHER_BLOCK_H,
            **extra,
        },
    )


# ---------------------------------------------------------------------------
# Weather block: dimensions and content
# ---------------------------------------------------------------------------

def test_weather_block_golden_image_has_correct_dimensions() -> None:
    """WeatherBlockRenderer must produce an image exactly matching the configured slot size."""
    renderer = WeatherBlockRenderer(icon_provider=NullWeatherIconProvider())
    result = renderer.render(_make_forecast(), _make_weather_panel())
    assert len(result) == 1
    placement = result[0]
    assert isinstance(placement, ImagePlacement)
    assert placement.image.width == _WEATHER_BLOCK_W
    assert placement.image.height == _WEATHER_BLOCK_H


def test_weather_block_placement_matches_configured_xy() -> None:
    """ImagePlacement coordinates must match the configured x/y in renderer_config."""
    renderer = WeatherBlockRenderer(icon_provider=NullWeatherIconProvider())
    result = renderer.render(_make_forecast(), _make_weather_panel())
    placement = result[0]
    assert placement.x == _WEATHER_BLOCK_X
    assert placement.y == _WEATHER_BLOCK_Y


def test_weather_block_is_not_blank() -> None:
    """The rendered weather block must not be a pure-white image — it must contain content."""
    renderer = WeatherBlockRenderer(icon_provider=NullWeatherIconProvider())
    result = renderer.render(_make_forecast(), _make_weather_panel())
    img = result[0].image
    # A threshold of 200 is well below pure white (255); any rendered text or
    # separator line produces pixels in the 0–180 range on a white background.
    _NOT_WHITE_THRESHOLD = 200
    pixels = list(img.getdata())
    assert any(p < _NOT_WHITE_THRESHOLD for p in pixels), "Weather block rendered as blank white image"


def test_weather_block_zero_precipitation_renders_without_error() -> None:
    """A forecast with zero precipitation everywhere must not raise."""
    forecast = WeatherForecast(
        location_name="Eichenau",
        provider="open_meteo",
        source_precision_hours=1,
        periods=tuple(
            _make_period("2026-04-27", h, precip_prob=0, precip_mm=0.0)
            for h in range(24)
        ),
    )
    renderer = WeatherBlockRenderer(icon_provider=NullWeatherIconProvider())
    result = renderer.render(forecast, _make_weather_panel(precip_prob_threshold=40, precip_mm_threshold=0.1))
    assert len(result) == 1
    assert isinstance(result[0], ImagePlacement)


def test_weather_block_low_precipitation_renders_without_error() -> None:
    """A forecast with precipitation just below the threshold must not raise."""
    forecast = WeatherForecast(
        location_name="Eichenau",
        provider="open_meteo",
        source_precision_hours=1,
        periods=tuple(
            _make_period("2026-04-27", h, precip_prob=39, precip_mm=0.09)
            for h in range(24)
        ),
    )
    renderer = WeatherBlockRenderer(icon_provider=NullWeatherIconProvider())
    result = renderer.render(forecast, _make_weather_panel(precip_prob_threshold=40, precip_mm_threshold=0.1))
    assert len(result) == 1


def test_weather_block_smaller_slot_renders_correctly() -> None:
    """The weather block must adapt to a smaller configured slot without raising."""
    renderer = WeatherBlockRenderer(icon_provider=NullWeatherIconProvider())
    result = renderer.render(_make_forecast(), _make_weather_panel(width=400, height=150))
    placement = result[0]
    assert isinstance(placement, ImagePlacement)
    assert placement.image.width == 400
    assert placement.image.height == 150


# ---------------------------------------------------------------------------
# SVG layout: full pipeline with fixed text blocks
# ---------------------------------------------------------------------------

def _layout_svg_with_slots(tmp_path: Path) -> Path:
    """Write a minimal 800×480 layout SVG with non-overlapping slot bounding boxes."""
    template = tmp_path / "layout.svg"
    template.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="800" height="480">
          <rect width="800" height="480" fill="white" />
          <text id="calendar" x="8" y="42" font-size="22"
                data-bbox-width="274" data-bbox-height="110" />
          <text id="trains" x="64" y="192" font-size="18"
                data-bbox-width="236" data-bbox-height="280" />
          <image id="weather_block" x="310" y="163" width="482" height="312" />
          <text id="last_update" x="8" y="476" font-size="10" />
        </svg>""",
        encoding="utf-8",
    )
    return template


def test_svg_layout_full_render_correct_dimensions(tmp_path: Path) -> None:
    """Full SVG layout render with fixed text blocks must produce an 800×480 image."""
    template = _layout_svg_with_slots(tmp_path)
    blocks = (
        DashboardTextBlock(slot="calendar", lines=("Monday", "27 April")),
        DashboardTextBlock(
            slot="trains",
            lines=(
                "Eichenau",
                "S4  18:44  Buchenau",
                "    18:52  Trudering",
                "    19:09  Geltendorf",
            ),
        ),
        DashboardTextBlock(slot="last_update", lines=("Last update: 2026-04-27 18:44",)),
    )
    img = SvgLayoutRenderer().render(
        template_path=template,
        blocks=blocks,
        width=_DASHBOARD_WIDTH,
        height=_DASHBOARD_HEIGHT,
    )
    assert img.size == (_DASHBOARD_WIDTH, _DASHBOARD_HEIGHT)


def test_svg_layout_no_slot_overlaps_in_example_template(tmp_path: Path) -> None:
    """The example layout SVG must not have overlapping slot bounding boxes."""
    import xml.etree.ElementTree as ET

    template = _layout_svg_with_slots(tmp_path)
    root = ET.parse(template).getroot()
    bboxes = collect_slot_bboxes(root)
    overlaps = check_slot_overlaps(bboxes)
    assert overlaps == [], f"Layout has overlapping slots: {overlaps}"


def test_svg_layout_long_german_station_name_does_not_raise(tmp_path: Path) -> None:
    """A very long German station name must render without error."""
    template = _layout_svg_with_slots(tmp_path)
    long_station = "München Hauptbahnhof Gleis 1–26 Fernbahnsteig"
    blocks = (
        DashboardTextBlock(
            slot="trains",
            lines=(
                long_station,
                "S4  18:44  Leuchtenbergring",
                "    18:52  Ostbahnhof",
            ),
        ),
    )
    img = SvgLayoutRenderer().render(
        template_path=template,
        blocks=blocks,
        width=_DASHBOARD_WIDTH,
        height=_DASHBOARD_HEIGHT,
    )
    assert img.size == (_DASHBOARD_WIDTH, _DASHBOARD_HEIGHT)


def test_svg_layout_saves_preview_image(tmp_path: Path) -> None:
    """When svg_output is provided the renderer must write an SVG file."""
    template = _layout_svg_with_slots(tmp_path)
    svg_out = tmp_path / "preview.svg"
    blocks = (
        DashboardTextBlock(slot="calendar", lines=("Monday", "27 April")),
    )
    SvgLayoutRenderer().render(
        template_path=template,
        blocks=blocks,
        width=_DASHBOARD_WIDTH,
        height=_DASHBOARD_HEIGHT,
        svg_output=svg_out,
    )
    assert svg_out.exists()
    assert svg_out.stat().st_size > 0
