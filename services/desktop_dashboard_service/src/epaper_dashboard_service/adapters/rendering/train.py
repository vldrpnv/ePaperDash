from __future__ import annotations

from epaper_dashboard_service.domain.i18n import ENGLISH, Translations
from epaper_dashboard_service.domain.models import (
    DashboardTextBlock,
    PanelDefinition,
    RichLine,
    StyledLine,
    TextSpan,
    TrainDeparture,
    TrainDepartures,
)
from epaper_dashboard_service.domain.ports import RendererPlugin


class TrainDepartureTextRenderer(RendererPlugin):
    """Render MVG departure entries as rich-text lines.

    Each departure is formatted as one ``RichLine`` (or ``StyledLine`` when
    ``departure-font-size`` is configured):

    - The station name header is shown in **bold**.
    - The line label (e.g. ``S4``) is shown in **bold**.
    - The scheduled time follows.
    - When the departure is cancelled the scheduled time is struck through and
      the localized cancellation label is appended.
    - When realtime information is available and differs from the scheduled
      time, the actual time is appended after the scheduled time.
    """

    name = "train_departures_text"
    supported_type = TrainDepartures

    def __init__(self, translations: Translations | None = None) -> None:
        self._translations = translations or ENGLISH

    def render(self, data: TrainDepartures, panel: PanelDefinition) -> tuple[DashboardTextBlock, ...]:
        station_line: RichLine = (TextSpan(text=data.station_name, bold=True),)
        departure_font_size = _departure_font_size(panel)
        station_break_dy: str = str(panel.renderer_config.get("station-break-dy", "1.6em"))
        departure_break_dy: str = str(panel.renderer_config.get("departure-break-dy", "1.8em"))
        lines: list[str | RichLine | StyledLine] = [station_line]
        for i, dep in enumerate(data.entries):
            main_spans, dest_text = _format_departure(dep, self._translations)
            main_dy = station_break_dy if i == 0 else departure_break_dy
            lines.append(StyledLine(spans=main_spans, font_size=departure_font_size, dy=main_dy))
            lines.append(StyledLine(
                spans=(TextSpan(text=dest_text),),
                font_size=departure_font_size,
                dy="1.1em",
            ))

        return (
            DashboardTextBlock(
                slot=panel.slot,
                lines=tuple(lines),
                attributes=_text_attributes(panel),
            ),
        )


def _format_departure(dep: TrainDeparture, translations: Translations) -> tuple[RichLine, str]:
    """Return (main RichLine with line+times, destination text)."""
    scheduled_str = dep.scheduled_time.strftime("%H:%M")
    dest_line = f"   {dep.destination}"

    if dep.cancelled:
        return (
            (
                TextSpan(text=dep.line, bold=True),
                TextSpan(text="  "),
                TextSpan(text=scheduled_str, strikethrough=True),
                TextSpan(text=f"  {translations.cancelled}"),
            ),
            dest_line,
        )

    spans: list[TextSpan] = [
        TextSpan(text=dep.line, bold=True),
        TextSpan(text="  "),
    ]

    if dep.actual_time is not None:
        actual_str = dep.actual_time.strftime("%H:%M")
        is_delayed = actual_str != scheduled_str
        spans.append(TextSpan(text=scheduled_str, strikethrough=is_delayed))
        if is_delayed:
            spans.append(TextSpan(text=f"  {actual_str}"))
    else:
        spans.append(TextSpan(text=scheduled_str))

    return tuple(spans), dest_line


def _departure_font_size(panel: PanelDefinition) -> int | None:
    """Return the configured departure font size, or ``None`` if not set."""
    value = panel.renderer_config.get("departure-font-size")
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _text_attributes(panel: PanelDefinition) -> dict[str, str]:
    allowed_keys = {"font-size", "font-family", "font-weight", "fill", "text-anchor"}
    return {
        key: str(value)
        for key, value in panel.renderer_config.items()
        if key in allowed_keys
    }
