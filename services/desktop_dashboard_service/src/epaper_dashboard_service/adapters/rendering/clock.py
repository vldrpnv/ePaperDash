from __future__ import annotations

from epaper_dashboard_service.domain.models import ClockTime, DashboardTextBlock, PanelDefinition
from epaper_dashboard_service.domain.ports import RendererPlugin


class ClockTextRenderer(RendererPlugin):
    """Render the current time from a ``ClockTime`` as a single text slot.

    ``renderer_config`` keys:
    - ``time_format``: ``strftime`` format string (default: ``"%H:%M"``).
    - SVG text attributes (``font-size``, ``font-family``, ``font-weight``,
      ``fill``, ``text-anchor``) are passed through to the ``<text>`` element.
    """

    name = "clock_text"
    supported_type = ClockTime

    def render(self, data: ClockTime, panel: PanelDefinition) -> tuple[DashboardTextBlock, ...]:
        time_format = str(panel.renderer_config.get("time_format", "%H:%M"))
        time_str = data.current_time.strftime(time_format)
        return (
            DashboardTextBlock(
                slot=panel.slot,
                lines=(time_str,),
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
