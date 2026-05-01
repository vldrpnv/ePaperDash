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


def test_renderer_shows_next_three_entries_regardless_of_date_distance() -> None:
    renderer = WasteCollectionTextRenderer()
    data = WasteCollectionSchedule(
        address_label="Ringstr. 12, Eichenau",
        reference_date=date(2024, 5, 1),
        entries=(
            WasteCollectionEntry(date=date(2024, 5, 1), waste_type="Restmülltonne"),
            WasteCollectionEntry(date=date(2024, 5, 2), waste_type="Biotonne"),
            WasteCollectionEntry(date=date(2024, 5, 4), waste_type="Papiertonne"),
            WasteCollectionEntry(date=date(2024, 5, 10), waste_type="Wertstofftonne"),  # 4th — excluded
        ),
    )

    blocks = renderer.render(data, _make_panel(**{"font-size": "20"}))

    assert len(blocks) == 1
    assert blocks[0].slot == "waste"
    assert len(blocks[0].lines) == 3
    # today: Mi, 01. Mai — bold + bigger
    today_line = blocks[0].lines[0]
    assert isinstance(today_line, StyledLine)
    assert today_line.spans[0].text == "Mi, 01. Mai · Restmülltonne"
    assert today_line.spans[0].bold is True
    # tomorrow: Do, 02. Mai — bold + bigger
    tomorrow_line = blocks[0].lines[1]
    assert isinstance(tomorrow_line, StyledLine)
    assert tomorrow_line.spans[0].text == "Do, 02. Mai · Biotonne"
    assert tomorrow_line.spans[0].bold is True
    # further out: Sa, 04. Mai — plain string
    other_line = blocks[0].lines[2]
    assert isinstance(other_line, str)
    assert other_line == "Sa, 04. Mai · Papiertonne"


def test_renderer_highlights_today_and_tomorrow_with_bold_larger_text() -> None:
    renderer = WasteCollectionTextRenderer()
    data = WasteCollectionSchedule(
        address_label="Ringstr. 12, Eichenau",
        reference_date=date(2024, 5, 1),
        entries=(
            WasteCollectionEntry(date=date(2024, 5, 1), waste_type="Restmülltonne"),
            WasteCollectionEntry(date=date(2024, 5, 2), waste_type="Biotonne"),
        ),
    )

    blocks = renderer.render(data, _make_panel(**{"font-size": "20"}))

    for line in blocks[0].lines:
        assert isinstance(line, StyledLine)
        assert line.font_size is not None
        assert line.font_size > 20
        assert all(isinstance(span, TextSpan) and span.bold for span in line.spans)


def test_renderer_shows_empty_state_when_no_entries() -> None:
    renderer = WasteCollectionTextRenderer()
    data = WasteCollectionSchedule(
        address_label="Ringstr. 12, Eichenau",
        reference_date=date(2024, 5, 1),
        entries=(),
    )

    blocks = renderer.render(data, _make_panel())

    assert blocks[0].lines == ("Keine bevorstehende Abholung",)
