from __future__ import annotations

from datetime import timedelta

from epaper_dashboard_service.domain.models import (
    CalendarDate,
    DashboardTextBlock,
    PanelDefinition,
    WeatherForecast,
    WeatherPeriod,
)
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
        show_provider = bool(panel.renderer_config.get("show_provider", False))
        location_line = data.location_name
        if show_provider:
            location_line = f"{location_line} ({data.provider})"

        periods = _select_weather_periods(data, panel)
        lines = [location_line]
        for period in periods:
            lines.append(
                (
                    f"{period.condition_icon} "
                    f"{period.start_time:%H:%M}-{period.end_time:%H:%M} "
                    f"{period.temperature_c:.0f}C "
                    f"{period.precipitation_probability_percent}%"
                )
            )

        return (
            DashboardTextBlock(
                slot=panel.slot,
                lines=tuple(lines),
                attributes=_text_attributes(panel),
            ),
        )


def _select_weather_periods(data: WeatherForecast, panel: PanelDefinition) -> tuple[WeatherPeriod, ...]:
    if not data.periods:
        return ()

    source_precision = data.source_precision_hours
    target_precision = int(panel.renderer_config.get("precision_hours", source_precision))
    days = max(1, int(panel.renderer_config.get("days", 3)))
    max_periods = max(1, int(panel.renderer_config.get("max_periods", 6)))

    horizon_end = data.periods[0].start_time + timedelta(days=days)
    filtered = tuple(period for period in data.periods if period.start_time < horizon_end)

    if target_precision >= source_precision and target_precision % source_precision == 0:
        filtered = _coarsen_weather_periods(filtered, source_precision, target_precision)

    return filtered[:max_periods]


def _coarsen_weather_periods(
    periods: tuple[WeatherPeriod, ...],
    source_precision_hours: int,
    target_precision_hours: int,
) -> tuple[WeatherPeriod, ...]:
    if not periods or target_precision_hours == source_precision_hours:
        return periods

    group_size = target_precision_hours // source_precision_hours
    grouped: list[WeatherPeriod] = []
    for index in range(0, len(periods), group_size):
        chunk = periods[index : index + group_size]
        if not chunk:
            continue
        representative = max(chunk, key=lambda period: period.precipitation_probability_percent)
        grouped.append(
            WeatherPeriod(
                start_time=chunk[0].start_time,
                end_time=chunk[-1].end_time,
                temperature_c=sum(period.temperature_c for period in chunk) / len(chunk),
                precipitation_probability_percent=max(
                    period.precipitation_probability_percent for period in chunk
                ),
                condition_label=representative.condition_label,
                condition_icon=representative.condition_icon,
                precipitation_mm=sum(period.precipitation_mm for period in chunk),
            )
        )

    return tuple(grouped)


def _text_attributes(panel: PanelDefinition) -> dict[str, str]:
    allowed_keys = {"font-size", "font-family", "font-weight", "fill", "text-anchor"}
    return {
        key: str(value)
        for key, value in panel.renderer_config.items()
        if key in allowed_keys
    }
