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
_MONTH_LABELS = (
    "Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
    "Jul", "Aug", "Sep", "Okt", "Nov", "Dez",
)


class WasteCollectionTextRenderer(RendererPlugin):
    name = "waste_collection_text"
    supported_type = WasteCollectionSchedule

    def render(self, data: WasteCollectionSchedule, panel: PanelDefinition) -> tuple[DashboardTextBlock, ...]:
        max_entries = _parse_max_entries(panel)
        visible_entries = data.entries[:max_entries]

        if visible_entries:
            lines = tuple(_render_entry(entry, data.reference_date, panel) for entry in visible_entries)
        else:
            lines = ("Keine bevorstehende Abholung",)

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
    label = _format_date_label(entry.date)
    text = f"{label} · {entry.waste_type}"
    if days_until <= 1:
        return StyledLine(
            spans=(TextSpan(text=text, bold=True),),
            font_size=_emphasis_font_size(panel),
        )
    return text


def _format_date_label(entry_date: date) -> str:
    weekday = _WEEKDAY_LABELS[entry_date.weekday()]
    month = _MONTH_LABELS[entry_date.month - 1]
    return f"{weekday}, {entry_date.day:02d}. {month}"


def _emphasis_font_size(panel: PanelDefinition) -> int:
    configured = panel.renderer_config.get("tomorrow-font-size")
    if configured is not None:
        return int(configured)

    base_size = panel.renderer_config.get("font-size")
    if base_size is not None:
        return int(base_size) + 4
    return 24


def _parse_max_entries(panel: PanelDefinition) -> int:
    raw_value = panel.renderer_config.get("max_entries", 3)
    try:
        return max(1, int(raw_value))
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid max_entries for waste_collection_text renderer: {raw_value!r}") from error


def _text_attributes(panel: PanelDefinition) -> dict[str, str]:
    allowed_keys = {"font-size", "font-family", "font-weight", "fill", "text-anchor"}
    return {
        key: str(value)
        for key, value in panel.renderer_config.items()
        if key in allowed_keys
    }
