from __future__ import annotations

from epaper_dashboard_service.domain.models import CalendarDate, DashboardTextBlock, PanelDefinition, WeatherForecast
from epaper_dashboard_service.domain.ports import RendererPlugin


class CalendarTextRenderer(RendererPlugin):
    name = "calendar_text"
    supported_type = CalendarDate

    def render(self, data: CalendarDate, panel: PanelDefinition) -> tuple[DashboardTextBlock, ...]:
        return (
            DashboardTextBlock(
                slot=panel.slot,
                lines=(
                    data.day_of_week,
                    f"{data.day} {data.month}",
                ),
                attributes=_text_attributes(panel),
            ),
        )


class WeatherTextRenderer(RendererPlugin):
    name = "weather_text"
    supported_type = WeatherForecast

    def render(self, data: WeatherForecast, panel: PanelDefinition) -> tuple[DashboardTextBlock, ...]:
        return (
            DashboardTextBlock(
                slot=panel.slot,
                lines=(
                    data.location_name,
                    data.condition,
                    f"{data.temperature_min_c:.1f}°C to {data.temperature_max_c:.1f}°C",
                    f"Precipitation {data.precipitation_probability_percent}%",
                ),
                attributes=_text_attributes(panel),
            ),
        )


def _text_attributes(panel: PanelDefinition) -> dict[str, str]:
    allowed_keys = {"font-size", "font-family", "font-weight", "fill", "text-anchor"}
    return {
        key: str(value)
        for key, value in panel.renderer_config.items()
        if key in allowed_keys
    }
