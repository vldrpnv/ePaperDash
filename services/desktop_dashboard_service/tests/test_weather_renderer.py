from __future__ import annotations

from datetime import datetime, timezone

from epaper_dashboard_service.adapters.rendering.text import WeatherTextRenderer
from epaper_dashboard_service.domain.models import PanelDefinition, WeatherForecast, WeatherPeriod


def _make_panel(**renderer_config) -> PanelDefinition:
    return PanelDefinition(
        source="weather_forecast",
        renderer="weather_text",
        slot="weather",
        source_config={},
        renderer_config=renderer_config,
    )


def _utc(hour: int) -> datetime:
    return datetime(2026, 4, 27, hour, 0, tzinfo=timezone.utc)


def test_weather_renderer_uses_icons_instead_of_condition_text() -> None:
    renderer = WeatherTextRenderer()
    data = WeatherForecast(
        location_name="Eichenau",
        provider="open_meteo",
        source_precision_hours=1,
        periods=(
            WeatherPeriod(
                start_time=_utc(8),
                end_time=_utc(9),
                temperature_c=12.4,
                precipitation_probability_percent=30,
                condition_label="Cloudy",
                condition_icon="☁",
            ),
        ),
    )

    block = renderer.render(data, _make_panel())[0]

    assert block.lines[0] == "Eichenau"
    assert any("☁" in line for line in block.lines[1:] if isinstance(line, str))
    assert all("Cloudy" not in line for line in block.lines[1:] if isinstance(line, str))


def test_weather_renderer_respects_precision_hours() -> None:
    renderer = WeatherTextRenderer()
    data = WeatherForecast(
        location_name="Eichenau",
        provider="open_meteo",
        source_precision_hours=1,
        periods=tuple(
            WeatherPeriod(
                start_time=_utc(hour),
                end_time=_utc(hour + 1),
                temperature_c=10.0 + hour,
                precipitation_probability_percent=10 * hour,
                condition_label="Sunny",
                condition_icon="☀",
            )
            for hour in range(6)
        ),
    )

    block = renderer.render(data, _make_panel(precision_hours=3, max_periods=3))[0]

    period_lines = [line for line in block.lines[1:] if isinstance(line, str)]
    assert len(period_lines) == 2
    assert "00:00-03:00" in period_lines[0]
    assert "03:00-06:00" in period_lines[1]


def test_weather_renderer_can_show_provider_label() -> None:
    renderer = WeatherTextRenderer()
    data = WeatherForecast(
        location_name="Eichenau",
        provider="met_no",
        source_precision_hours=1,
        periods=(
            WeatherPeriod(
                start_time=_utc(8),
                end_time=_utc(9),
                temperature_c=12.0,
                precipitation_probability_percent=20,
                condition_label="Partly cloudy",
                condition_icon="⛅",
            ),
        ),
    )

    block = renderer.render(data, _make_panel(show_provider=True))[0]

    assert block.lines[0] == "Eichenau (met_no)"
