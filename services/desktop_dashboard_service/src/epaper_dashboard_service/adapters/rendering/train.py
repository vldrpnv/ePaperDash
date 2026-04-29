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
      time, only the actual (realtime) departure time is shown in **bold** —
      the scheduled time is hidden so the display stays clean and unambiguous.
    - The first (next) departure is rendered at ``first-departure-font-size``
      when configured, giving it visual emphasis over the following rows.
    """

    name = "train_departures_text"
    supported_type = TrainDepartures

    def render(self, data: TrainDepartures, panel: PanelDefinition) -> tuple[DashboardTextBlock, ...]:
        station_name_font_size_raw = panel.renderer_config.get("station-name-font-size")
        station_name_font_size: int | None = (
            int(station_name_font_size_raw) if station_name_font_size_raw else None
        )
        show_line = _parse_show_line(panel.renderer_config.get("show-line", "true"))
        station_rich_line: RichLine = (TextSpan(text=data.station_name, bold=True),)
        if station_name_font_size is not None:
            station_entry: RichLine | StyledLine = StyledLine(
                spans=station_rich_line, font_size=station_name_font_size
            )
        else:
            station_entry = station_rich_line
        departure_font_size = _departure_font_size(panel)
        first_departure_font_size = _first_departure_font_size(panel)
        station_break_dy: str = str(panel.renderer_config.get("station-break-dy", "1.6em"))
        departure_break_dy: str = str(panel.renderer_config.get("departure-break-dy", "1.8em"))
        lines: list[str | RichLine | StyledLine] = [station_entry]
        prev_line_label: str | None = None
        for i, dep in enumerate(data.entries):
            show_label = dep.line != prev_line_label
            prev_line_label = dep.line
            main_spans = _format_departure_timetable(dep, show_label, show_line=show_line)
            main_dy = station_break_dy if i == 0 else departure_break_dy
            font_size = first_departure_font_size if i == 0 else departure_font_size
            lines.append(StyledLine(spans=main_spans, font_size=font_size, dy=main_dy))

        return (
            DashboardTextBlock(
                slot=panel.slot,
                lines=tuple(lines),
                attributes=_text_attributes(panel),
            ),
        )


def _format_departure_timetable(dep: TrainDeparture, show_line_label: bool, show_line: bool = True) -> RichLine:
    """Return a single ``RichLine`` containing label, times, and destination.

    When *show_line* is ``True`` and *show_line_label* is ``True``, the line
    label (e.g. ``S4``) is rendered in **bold**.  When *show_line_label* is
    ``False`` (repeated label), it is replaced by an equal-width run of spaces
    so the time column stays visually aligned.  When *show_line* is ``False``
    the prefix is omitted entirely (no label, no padding).

    Delayed departures show only the actual (realtime) time in **bold** — the
    scheduled time is omitted entirely so the display stays clean and avoids
    showing two clock times side-by-side.  Cancelled departures show the
    scheduled time struck through followed by ``Cancelled``.  The destination
    always appears last on the same row.
    """
    scheduled_str = dep.scheduled_time.strftime("%H:%M")

    if not show_line:
        prefix: tuple[TextSpan, ...] = ()
    elif show_line_label:
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
        if is_delayed:
            # Show only the actual time in bold; hide the scheduled time so
            # two clock values don't appear side-by-side.
            time_spans.append(TextSpan(text=actual_str, bold=True))
        else:
            time_spans.append(TextSpan(text=scheduled_str))
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


def _first_departure_font_size(panel: PanelDefinition) -> int | None:
    """Return the font size for the first (next) departure, falling back to departure-font-size.

    When ``first-departure-font-size`` is set in renderer_config it is used for
    the first departure row only, giving it visual emphasis over subsequent rows.
    Falls back to ``departure-font-size`` when not set.
    """
    value = panel.renderer_config.get("first-departure-font-size")
    if value is None:
        return _departure_font_size(panel)
    try:
        return int(value)
    except (ValueError, TypeError):
        return _departure_font_size(panel)


def _text_attributes(panel: PanelDefinition) -> dict[str, str]:
    allowed_keys = {"font-size", "font-family", "font-weight", "fill", "text-anchor"}
    return {
        key: str(value)
        for key, value in panel.renderer_config.items()
        if key in allowed_keys
    }


def _parse_show_line(value: object) -> bool:
    """Coerce the ``show-line`` config value to bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() not in ("false", "0", "no", "off")
    return bool(value)
