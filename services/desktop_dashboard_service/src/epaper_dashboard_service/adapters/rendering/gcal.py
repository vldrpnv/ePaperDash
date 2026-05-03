"""Renderer for Google Calendar events."""
from __future__ import annotations

from datetime import date, timedelta

from epaper_dashboard_service.domain.models import (
    DashboardTextBlock,
    GoogleCalendarEvent,
    GoogleCalendarEvents,
    PanelDefinition,
)
from epaper_dashboard_service.domain.ports import RendererPlugin


_ALL_DAY_BULLET = "•"
_DISPLAY_DAYS = 3
_MAX_EVENTS_PER_DAY = 5


class GoogleCalendarTextRenderer(RendererPlugin):
    """Render today and the next two days into three dedicated text slots."""

    name = "google_calendar_text"
    supported_type = GoogleCalendarEvents

    def render(
        self, data: GoogleCalendarEvents, panel: PanelDefinition
    ) -> tuple[DashboardTextBlock, ...]:
        max_events_per_day = int(panel.renderer_config.get("max-events-per-day", _MAX_EVENTS_PER_DAY))
        attributes = _text_attributes(panel)
        blocks: list[DashboardTextBlock] = []

        for day_offset in range(_DISPLAY_DAYS):
            event_day = data.reference_date + timedelta(days=day_offset)
            lines = [_format_day_label(event_day, day_offset)]
            day_events = [
                event
                for event in data.events
                if event.event_date == event_day
            ][:max_events_per_day]
            if day_events:
                lines.extend(_format_event(event) for event in day_events)
            else:
                lines.append("No events")

            blocks.append(
                DashboardTextBlock(
                    slot=f"{panel.slot}_{day_offset}",
                    lines=tuple(lines),
                    attributes=attributes,
                )
            )

        return tuple(blocks)


def _format_event(event: GoogleCalendarEvent) -> str:
    if event.all_day or event.start_time is None:
        return f"{_ALL_DAY_BULLET} {event.title}"
    return f"{event.start_time.strftime('%H:%M')} {event.title}"


def _format_day_label(event_day: date, day_offset: int) -> str:
    suffix = ""
    if day_offset == 0:
        suffix = ", today"
    elif day_offset == 1:
        suffix = ", tomorrow"
    return f"{event_day.strftime('%A')}{suffix}"


def _text_attributes(panel: PanelDefinition) -> dict[str, str]:
    allowed_keys = {"font-size", "font-family", "font-weight", "fill", "text-anchor"}
    return {
        key: str(value)
        for key, value in panel.renderer_config.items()
        if key in allowed_keys
    }
