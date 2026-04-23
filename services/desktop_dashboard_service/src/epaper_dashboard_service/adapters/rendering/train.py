from __future__ import annotations

from epaper_dashboard_service.domain.models import (
    DashboardTextBlock,
    PanelDefinition,
    RichLine,
    TextSpan,
    TrainDeparture,
    TrainDepartures,
)
from epaper_dashboard_service.domain.ports import RendererPlugin


class TrainDepartureTextRenderer(RendererPlugin):
    """Render MVG departure entries as rich-text lines.

    Each departure is formatted as one ``RichLine``:

    - The line label (e.g. ``S4``) is shown in **bold**.
    - The scheduled time follows.
    - When the departure is cancelled the scheduled time is struck through and
      ``Cancelled`` is appended.
    - When realtime information is available and differs from the scheduled
      time, the actual time is appended after the scheduled time.
    """

    name = "train_departures_text"
    supported_type = TrainDepartures

    def render(self, data: TrainDepartures, panel: PanelDefinition) -> tuple[DashboardTextBlock, ...]:
        header_line: str = data.station_name
        entry_lines: list[RichLine] = [_format_departure(dep) for dep in data.entries]

        lines: tuple[str | RichLine, ...] = (header_line, *entry_lines)
        return (
            DashboardTextBlock(
                slot=panel.slot,
                lines=lines,
                attributes=_text_attributes(panel),
            ),
        )


def _format_departure(dep: TrainDeparture) -> RichLine:
    scheduled_str = dep.scheduled_time.strftime("%H:%M")

    if dep.cancelled:
        return (
            TextSpan(text=dep.line, bold=True),
            TextSpan(text="  "),
            TextSpan(text=scheduled_str, strikethrough=True),
            TextSpan(text="  Cancelled"),
        )

    spans: list[TextSpan] = [
        TextSpan(text=dep.line, bold=True),
        TextSpan(text="  "),
        TextSpan(text=scheduled_str),
    ]

    if dep.actual_time is not None:
        actual_str = dep.actual_time.strftime("%H:%M")
        if actual_str != scheduled_str:
            spans.append(TextSpan(text=f"  {actual_str}"))

    return tuple(spans)


def _text_attributes(panel: PanelDefinition) -> dict[str, str]:
    allowed_keys = {"font-size", "font-family", "font-weight", "fill", "text-anchor"}
    return {
        key: str(value)
        for key, value in panel.renderer_config.items()
        if key in allowed_keys
    }
