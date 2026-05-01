from __future__ import annotations

from datetime import date

from epaper_dashboard_service.domain.models import (
    DashboardTextBlock,
    PanelDefinition,
    StyledLine,
    TextSpan,
    WasteCollectionEntry,
    WasteCollectionSchedule,
)
from epaper_dashboard_service.domain.ports import RendererPlugin

_WEEKDAY_LABELS = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")


class WasteCollectionTextRenderer(RendererPlugin):
    name = "waste_collection_text"
    supported_type = WasteCollectionSchedule

    def render(self, data: WasteCollectionSchedule, panel: PanelDefinition) -> tuple[DashboardTextBlock, ...]:
        days = max(1, int(panel.renderer_config.get("days", 3)))
        visible_entries = tuple(
            entry
            for entry in data.entries
            if 0 <= (entry.date - data.reference_date).days < days
        )

        if visible_entries:
            lines = tuple(_render_entry(entry, data.reference_date, panel) for entry in visible_entries)
        else:
            lines = (f"Keine Abholung in den nächsten {days} Tagen",)

        return (
            DashboardTextBlock(
                slot=panel.slot,
                lines=lines,
                attributes=_text_attributes(panel),
            ),
        )


def _render_entry(
    entry: WasteCollectionEntry,
    reference_date: date,
    panel: PanelDefinition,
) -> str | StyledLine:
    days_until = (entry.date - reference_date).days
    if days_until == 0:
        return f"Heute · {entry.waste_type}"

    label = "Morgen" if days_until == 1 else f"{_WEEKDAY_LABELS[entry.date.weekday()]} {entry.date:%d.%m.}"
    text = f"{label} · {entry.waste_type}"
    if days_until == 1:
        return StyledLine(
            spans=(TextSpan(text=text, bold=True),),
            font_size=_tomorrow_font_size(panel),
        )
    return text


def _tomorrow_font_size(panel: PanelDefinition) -> int:
    configured = panel.renderer_config.get("tomorrow-font-size")
    if configured is not None:
        return int(configured)

    base_size = panel.renderer_config.get("font-size")
    if base_size is not None:
        return int(base_size) + 4
    return 24


def _text_attributes(panel: PanelDefinition) -> dict[str, str]:
    allowed_keys = {"font-size", "font-family", "font-weight", "fill", "text-anchor"}
    return {
        key: str(value)
        for key, value in panel.renderer_config.items()
        if key in allowed_keys
    }
