from __future__ import annotations

from datetime import date

from epaper_dashboard_service.adapters.rendering.waste import WasteCollectionTextRenderer
from epaper_dashboard_service.domain.models import (
    PanelDefinition,
    StyledLine,
    TextSpan,
    WasteCollectionEntry,
    WasteCollectionSchedule,
)


def _make_panel(**renderer_config) -> PanelDefinition:
    return PanelDefinition(
        source="ffb_waste_collection",
        renderer="waste_collection_text",
        slot="waste",
        source_config={},
        renderer_config=renderer_config,
    )


def test_renderer_limits_output_to_next_three_days() -> None:
    renderer = WasteCollectionTextRenderer()
    data = WasteCollectionSchedule(
        address_label="Ringstr. 12, Eichenau",
        reference_date=date(2024, 5, 1),
        entries=(
            WasteCollectionEntry(date=date(2024, 5, 1), waste_type="Restmülltonne"),
            WasteCollectionEntry(date=date(2024, 5, 2), waste_type="Biotonne"),
            WasteCollectionEntry(date=date(2024, 5, 4), waste_type="Papiertonne"),
        ),
    )

    blocks = renderer.render(data, _make_panel(**{"font-size": "20"}))

    assert len(blocks) == 1
    assert blocks[0].slot == "waste"
    assert len(blocks[0].lines) == 2
    assert isinstance(blocks[0].lines[0], str)
    assert blocks[0].lines[0] == "Heute · Restmülltonne"
    tomorrow_line = blocks[0].lines[1]
    assert isinstance(tomorrow_line, StyledLine)
    assert len(tomorrow_line.spans) == 1
    assert tomorrow_line.spans[0].text == "Morgen · Biotonne"


def test_renderer_highlights_tomorrow_with_bold_larger_text() -> None:
    renderer = WasteCollectionTextRenderer()
    data = WasteCollectionSchedule(
        address_label="Ringstr. 12, Eichenau",
        reference_date=date(2024, 5, 1),
        entries=(
            WasteCollectionEntry(date=date(2024, 5, 2), waste_type="Biotonne"),
        ),
    )

    blocks = renderer.render(data, _make_panel(**{"font-size": "20"}))

    line = blocks[0].lines[0]
    assert isinstance(line, StyledLine)
    assert line.font_size is not None
    assert line.font_size > 20
    assert all(isinstance(span, TextSpan) and span.bold for span in line.spans)


def test_renderer_shows_empty_state_when_no_collections_are_due() -> None:
    renderer = WasteCollectionTextRenderer()
    data = WasteCollectionSchedule(
        address_label="Ringstr. 12, Eichenau",
        reference_date=date(2024, 5, 1),
        entries=(
            WasteCollectionEntry(date=date(2024, 5, 7), waste_type="Biotonne"),
        ),
    )

    blocks = renderer.render(data, _make_panel())

    assert blocks[0].lines == ("Keine Abholung in den nächsten 3 Tagen",)
