from __future__ import annotations

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
    """Render MVG departure entries as rich-text timetable lines.

    Each departure is formatted as a single ``StyledLine`` (timetable row):

    - The station name header is shown in **bold**.
    - The line label (e.g. ``S4``) is shown in **bold** for the first
      occurrence; subsequent departures of the same line use space padding
      so the time column stays aligned.
    - The scheduled time follows.
    - The destination appears on the same row after the time.
    - When the departure is cancelled the scheduled time is struck through and
      ``Cancelled`` is appended before the destination.
    - When realtime information is available and differs from the scheduled
      time, the actual time is shown in **bold** after the (struck) scheduled
      time.
    """

    name = "train_departures_text"
    supported_type = TrainDepartures

    def render(self, data: TrainDepartures, panel: PanelDefinition) -> tuple[DashboardTextBlock, ...]:
        station_line: RichLine = (TextSpan(text=data.station_name, bold=True),)
        departure_font_size = _departure_font_size(panel)
        station_break_dy: str = str(panel.renderer_config.get("station-break-dy", "1.6em"))
        departure_break_dy: str = str(panel.renderer_config.get("departure-break-dy", "1.8em"))
        lines: list[str | RichLine | StyledLine] = [station_line]
        prev_line_label: str | None = None
        for i, dep in enumerate(data.entries):
            show_label = dep.line != prev_line_label
            prev_line_label = dep.line
            main_spans = _format_departure_timetable(dep, show_label)
            main_dy = station_break_dy if i == 0 else departure_break_dy
            lines.append(StyledLine(spans=main_spans, font_size=departure_font_size, dy=main_dy))

        return (
            DashboardTextBlock(
                slot=panel.slot,
                lines=tuple(lines),
                attributes=_text_attributes(panel),
            ),
        )


def _format_departure_timetable(dep: TrainDeparture, show_line_label: bool) -> RichLine:
    """Return a single ``RichLine`` containing label, times, and destination.

    When *show_line_label* is ``True`` the line label (e.g. ``S4``) is
    rendered in **bold**.  When ``False`` (repeated label) it is replaced by
    an equal-width run of spaces so the time column stays visually aligned.

    Delayed departures show the scheduled time struck through followed by the
    actual time in **bold**.  Cancelled departures show the scheduled time
    struck through followed by ``Cancelled``.  The destination always appears
    last on the same row.
    """
    scheduled_str = dep.scheduled_time.strftime("%H:%M")

    if show_line_label:
        prefix: tuple[TextSpan, ...] = (
            TextSpan(text=dep.line, bold=True),
            TextSpan(text="  "),
        )
    else:
        prefix = (TextSpan(text=" " * (len(dep.line) + 2)),)

    if dep.cancelled:
        return prefix + (
            TextSpan(text=scheduled_str, strikethrough=True),
            TextSpan(text="  Cancelled"),
            TextSpan(text=f"  {dep.destination}"),
        )

    time_spans: list[TextSpan] = []
    if dep.actual_time is not None:
        actual_str = dep.actual_time.strftime("%H:%M")
        is_delayed = actual_str != scheduled_str
        time_spans.append(TextSpan(text=scheduled_str, strikethrough=is_delayed))
        if is_delayed:
            time_spans.append(TextSpan(text=f"  {actual_str}", bold=True))
    else:
        time_spans.append(TextSpan(text=scheduled_str))

    return prefix + tuple(time_spans) + (TextSpan(text=f"  {dep.destination}"),)


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
