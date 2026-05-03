"""Trello card text renderer.

Renders open Trello cards as a ``DashboardTextBlock``.  Cards are grouped by
list name: each list name is emitted as a bold header line, followed by the
card names prefixed with ``•``.
"""
from __future__ import annotations

from epaper_dashboard_service.domain.models import (
    DashboardTextBlock,
    PanelDefinition,
    RichLine,
    TextSpan,
    TrelloCards,
)
from epaper_dashboard_service.domain.ports import RendererPlugin


class TrelloCardsTextRenderer(RendererPlugin):
    name = "trello_cards_text"
    supported_type = TrelloCards

    def render(self, data: TrelloCards, panel: PanelDefinition) -> tuple[DashboardTextBlock, ...]:
        if not data.cards:
            return (
                DashboardTextBlock(
                    slot=panel.slot,
                    lines=("No cards",),
                    attributes=_text_attributes(panel),
                ),
            )

        lines: list[str | RichLine] = []
        current_list: str | None = None
        for card in data.cards:
            if card.list_name != current_list:
                current_list = card.list_name
                lines.append((TextSpan(text=card.list_name, bold=True),))
            lines.append(f"\u2022 {card.name}")

        return (
            DashboardTextBlock(
                slot=panel.slot,
                lines=tuple(lines),
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
