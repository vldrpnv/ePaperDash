"""Renderer for Google Calendar events.

Produces a compact ``DashboardTextBlock`` containing up to ``max_events``
lines for today's events.  Each line follows one of two formats:

- All-day event: ``"• Event title"``
- Timed event:   ``"HH:MM Event title"``  (uses the start time only)

The slot is the SVG element identified by ``panel.slot``.  Standard text
attributes (``font-size``, ``font-family``, ``fill``) are forwarded from
``renderer_config`` to the target ``<text>`` element.
"""
from __future__ import annotations

from epaper_dashboard_service.domain.models import (
    DashboardTextBlock,
    GoogleCalendarEvent,
    GoogleCalendarEvents,
    PanelDefinition,
)
from epaper_dashboard_service.domain.ports import RendererPlugin


_ALL_DAY_BULLET = "•"


class GoogleCalendarTextRenderer(RendererPlugin):
    """Render today's Google Calendar events as plain text lines."""

    name = "google_calendar_text"
    supported_type = GoogleCalendarEvents

    def render(
        self, data: GoogleCalendarEvents, panel: PanelDefinition
    ) -> tuple[DashboardTextBlock, ...]:
        lines: list[str] = [_format_event(e) for e in data.events]
        if not lines:
            lines = ["No events"]

        return (
            DashboardTextBlock(
                slot=panel.slot,
                lines=tuple(lines),
                attributes=_text_attributes(panel),
            ),
        )


def _format_event(event: GoogleCalendarEvent) -> str:
    if event.all_day or event.start_time is None:
        return f"{_ALL_DAY_BULLET} {event.title}"
    return f"{event.start_time.strftime('%H:%M')} {event.title}"


def _text_attributes(panel: PanelDefinition) -> dict[str, str]:
    allowed_keys = {"font-size", "font-family", "font-weight", "fill", "text-anchor"}
    return {
        key: str(value)
        for key, value in panel.renderer_config.items()
        if key in allowed_keys
    }
