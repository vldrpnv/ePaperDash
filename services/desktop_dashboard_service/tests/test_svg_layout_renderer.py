from __future__ import annotations

import logging
from pathlib import Path
import xml.etree.ElementTree as ET

from epaper_dashboard_service.adapters.layout.svg import (
    SvgLayoutRenderer,
    _fit_font_size,
    check_content_overflow,
    check_slot_overlaps,
    collect_slot_bboxes,
    extract_image_slots,
    extract_text_slots,
)
from epaper_dashboard_service.domain.models import DashboardTextBlock, StyledLine, TextSpan


def _simple_svg(tmp_path: Path, extra_attrs: str = "") -> Path:
    template = tmp_path / "layout.svg"
    template.write_text(
        f"""<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">
          <rect width="200" height="100" fill="white" />
          <text id="slot" x="10" y="20" font-size="14" {extra_attrs}>placeholder</text>
        </svg>""",
        encoding="utf-8",
    )
    return template


def test_svg_layout_renderer_updates_multiline_text(tmp_path: Path) -> None:
    template = tmp_path / "layout.svg"
    template.write_text(
        """
        <svg xmlns=\"http://www.w3.org/2000/svg\" width=\"200\" height=\"100\">
          <rect width=\"200\" height=\"100\" fill=\"white\" />
          <text id=\"weather\" x=\"10\" y=\"20\" font-size=\"14\">placeholder</text>
        </svg>
        """,
        encoding="utf-8",
    )

    image = SvgLayoutRenderer().render(
        template_path=template,
        blocks=(DashboardTextBlock(slot="weather", lines=("Berlin", "Sunny")),),
        width=200,
        height=100,
    )

    assert image.size == (200, 100)


def test_svg_layout_renderer_renders_rich_text_spans(tmp_path: Path) -> None:
    template = _simple_svg(tmp_path)
    rich_line = (
        TextSpan(text="S4", bold=True),
        TextSpan(text="  10:00"),
        TextSpan(text="  10:03"),
    )
    block = DashboardTextBlock(slot="slot", lines=(rich_line,))

    image = SvgLayoutRenderer().render(template_path=template, blocks=(block,), width=200, height=100)
    assert image.size == (200, 100)


def test_svg_layout_renderer_rich_line_emits_tspan_with_bold(tmp_path: Path) -> None:
    """Bold spans must carry font-weight=bold in the produced SVG."""
    import xml.etree.ElementTree as _ET

    template = _simple_svg(tmp_path)
    rich_line = (
        TextSpan(text="S4", bold=True),
        TextSpan(text="  10:00"),
    )
    block = DashboardTextBlock(slot="slot", lines=(rich_line,))

    tree = _ET.parse(template)
    root = tree.getroot()
    SvgLayoutRenderer()._apply_text_block(root, block)

    text_el = next(el for el in root.iter() if el.get("id") == "slot")
    tspans = list(text_el)
    bold_tspans = [t for t in tspans if t.get("font-weight") == "bold"]
    assert bold_tspans, "Expected at least one tspan with font-weight=bold"
    assert bold_tspans[0].text == "S4"


def test_svg_layout_renderer_strikethrough_span(tmp_path: Path) -> None:
    import xml.etree.ElementTree as _ET

    template = _simple_svg(tmp_path)
    rich_line = (
        TextSpan(text="S3", bold=True),
        TextSpan(text="  10:15", strikethrough=True),
        TextSpan(text="  Cancelled"),
    )
    block = DashboardTextBlock(slot="slot", lines=(rich_line,))

    # The marking step: _apply_text_block sets text-decoration on the tspan.
    tree = _ET.parse(template)
    root = tree.getroot()
    SvgLayoutRenderer()._apply_text_block(root, block)

    text_el = next(el for el in root.iter() if el.get("id") == "slot")
    struck = [t for t in text_el if t.get("text-decoration") == "line-through"]
    assert len(struck) == 1
    assert "10:15" in struck[0].text


def test_svg_layout_renderer_strikethrough_injects_line_element(tmp_path: Path) -> None:
    """Full render: a struck span must produce a <line> element in the output SVG."""
    import xml.etree.ElementTree as _ET
    from epaper_dashboard_service.adapters.layout.svg import _inject_strikethrough_lines, SVG_NS

    template = _simple_svg(tmp_path)
    rich_line = (
        TextSpan(text="S3", bold=True),
        TextSpan(text="  10:15", strikethrough=True),
        TextSpan(text="  Cancelled"),
    )
    block = DashboardTextBlock(slot="slot", lines=(rich_line,))

    tree = _ET.parse(template)
    root = tree.getroot()
    SvgLayoutRenderer()._apply_text_block(root, block)
    text_el = next(el for el in root.iter() if el.get("id") == "slot")
    _inject_strikethrough_lines(root, text_el)

    line_els = [el for el in root.iter() if el.tag == f"{{{SVG_NS}}}line"]
    assert len(line_els) == 1, "Expected exactly one <line> element for the struck span"
    assert line_els[0].get("stroke") == "black"


def test_svg_layout_renderer_auto_font_size_from_bbox(tmp_path: Path) -> None:
    """When data-bbox-width/height are present, font-size is calculated automatically."""
    import xml.etree.ElementTree as _ET

    template = _simple_svg(tmp_path, extra_attrs='data-bbox-width="700" data-bbox-height="120"')
    block = DashboardTextBlock(slot="slot", lines=("Eichenau", "S4  10:00", "S4  10:15"))

    tree = _ET.parse(template)
    root = tree.getroot()
    SvgLayoutRenderer()._apply_text_block(root, block)

    text_el = next(el for el in root.iter() if el.get("id") == "slot")
    font_size = int(text_el.get("font-size", "0"))
    assert font_size > 0


def test_fit_font_size_respects_width_constraint() -> None:
    size = _fit_font_size(["Hello World"], bbox_width=50, bbox_height=500)
    assert size <= 20


def test_fit_font_size_respects_height_constraint() -> None:
    size = _fit_font_size(["A", "B", "C"], bbox_width=800, bbox_height=30)
    assert size <= 15


def test_fit_font_size_returns_minimum_for_empty_lines() -> None:
    size = _fit_font_size([], bbox_width=200, bbox_height=100)
    assert size == 8  # _MIN_FONT_SIZE


def test_extract_image_slots_returns_geometry_from_svg(tmp_path: Path) -> None:
    template = tmp_path / "layout.svg"
    template.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="800" height="480">
          <image id="image_pool" x="480" y="20" width="300" height="200" />
        </svg>""",
        encoding="utf-8",
    )

    slots = extract_image_slots(template)

    assert slots == {"image_pool": {"x": 480, "y": 20, "width": 300, "height": 200}}


def test_extract_image_slots_returns_empty_for_svg_without_image_elements(tmp_path: Path) -> None:
    template = tmp_path / "layout.svg"
    template.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="800" height="480">
          <rect width="800" height="480" fill="white" />
          <text id="weather" x="10" y="20">placeholder</text>
        </svg>""",
        encoding="utf-8",
    )

    assert extract_image_slots(template) == {}


def test_extract_image_slots_returns_empty_when_file_missing(tmp_path: Path) -> None:
    assert extract_image_slots(tmp_path / "nonexistent.svg") == {}


def test_extract_text_slots_returns_ids_for_text_elements(tmp_path: Path) -> None:
    template = tmp_path / "layout.svg"
    template.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="800" height="480">
          <text id="calendar" x="10" y="20" />
          <text id="last_update" x="8" y="476" />
          <rect width="800" height="480" fill="white" />
        </svg>""",
        encoding="utf-8",
    )

    assert extract_text_slots(template) == {"calendar", "last_update"}


def test_extract_text_slots_returns_empty_when_file_missing(tmp_path: Path) -> None:
    assert extract_text_slots(tmp_path / "nonexistent.svg") == set()


def test_example_layout_separates_calendar_block_waste_and_trains_slots() -> None:
    template = Path(__file__).resolve().parents[1] / "examples" / "layout_daytime.svg"

    root = ET.parse(template).getroot()
    bboxes = collect_slot_bboxes(root)

    assert bboxes["gcal_events"] == (196.0, 198.0, 596.0, 124.0)
    assert bboxes["waste"] == (8.0, 304.0, 168.0, 60.0)
    assert bboxes["trains"] == (244.0, 340.0, 280.0, 130.0)
    assert check_slot_overlaps(bboxes) == []


def test_svg_layout_renderer_strips_image_placeholders(tmp_path: Path) -> None:
    """<image id="..."> placeholder elements must not appear in the rasterised output."""
    template = tmp_path / "layout.svg"
    template.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">
          <rect width="200" height="100" fill="white" />
          <image id="photo_slot" x="0" y="0" width="100" height="100" />
        </svg>""",
        encoding="utf-8",
    )

    # Rendering must succeed (cairosvg would error on unresolvable href if not stripped)
    image = SvgLayoutRenderer().render(
        template_path=template,
        blocks=(),
        width=200,
        height=100,
    )
    assert image.size == (200, 100)


def test_svg_layout_renderer_clears_slot_text_for_unavailable_panel(tmp_path: Path) -> None:
    import xml.etree.ElementTree as _ET

    template = _simple_svg(tmp_path)
    tree = _ET.parse(template)
    root = tree.getroot()

    renderer = SvgLayoutRenderer()
    renderer._clear_text_slot(root, "slot")

    text_el = next(el for el in root.iter() if el.get("id") == "slot")
    assert text_el.text == ""
    assert list(text_el) == []


# ---------------------------------------------------------------------------
# collect_slot_bboxes
# ---------------------------------------------------------------------------


def test_collect_slot_bboxes_returns_image_slot_geometry(tmp_path: Path) -> None:
    import xml.etree.ElementTree as _ET

    svg = tmp_path / "layout.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="800" height="480">
          <image id="photo" x="500" y="10" width="280" height="200" />
        </svg>""",
        encoding="utf-8",
    )
    root = _ET.parse(svg).getroot()
    bboxes = collect_slot_bboxes(root)
    assert bboxes == {"photo": (500.0, 10.0, 280.0, 200.0)}


def test_collect_slot_bboxes_returns_text_slot_with_data_bbox(tmp_path: Path) -> None:
    import xml.etree.ElementTree as _ET

    svg = tmp_path / "layout.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="800" height="480">
          <text id="trains" x="10" y="300"
                data-bbox-width="460" data-bbox-height="150">placeholder</text>
        </svg>""",
        encoding="utf-8",
    )
    root = _ET.parse(svg).getroot()
    bboxes = collect_slot_bboxes(root)
    assert bboxes == {"trains": (10.0, 300.0, 460.0, 150.0)}


def test_collect_slot_bboxes_ignores_text_without_data_bbox(tmp_path: Path) -> None:
    import xml.etree.ElementTree as _ET

    svg = tmp_path / "layout.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="800" height="480">
          <text id="calendar" x="10" y="50" font-size="48">placeholder</text>
        </svg>""",
        encoding="utf-8",
    )
    root = _ET.parse(svg).getroot()
    assert collect_slot_bboxes(root) == {}


# ---------------------------------------------------------------------------
# check_slot_overlaps
# ---------------------------------------------------------------------------


def test_check_slot_overlaps_detects_overlapping_boxes() -> None:
    bboxes = {
        "slot_a": (0.0, 0.0, 100.0, 50.0),
        "slot_b": (80.0, 30.0, 100.0, 50.0),  # overlaps slot_a
    }
    overlaps = check_slot_overlaps(bboxes)
    assert len(overlaps) == 1
    assert set(overlaps[0]) == {"slot_a", "slot_b"}


def test_check_slot_overlaps_no_overlap_horizontal() -> None:
    bboxes = {
        "left": (0.0, 0.0, 100.0, 50.0),
        "right": (100.0, 0.0, 100.0, 50.0),  # touches but does not share area
    }
    assert check_slot_overlaps(bboxes) == []


def test_check_slot_overlaps_no_overlap_vertical() -> None:
    bboxes = {
        "top": (0.0, 0.0, 200.0, 100.0),
        "bottom": (0.0, 100.0, 200.0, 100.0),  # touches but does not share area
    }
    assert check_slot_overlaps(bboxes) == []


def test_check_slot_overlaps_single_slot_never_overlaps() -> None:
    bboxes = {"only": (0.0, 0.0, 800.0, 480.0)}
    assert check_slot_overlaps(bboxes) == []


def test_check_slot_overlaps_three_slots_two_pairs() -> None:
    bboxes = {
        "a": (0.0, 0.0, 200.0, 100.0),
        "b": (100.0, 50.0, 200.0, 100.0),  # overlaps a
        "c": (500.0, 400.0, 100.0, 50.0),  # no overlap with a or b
    }
    overlaps = check_slot_overlaps(bboxes)
    assert len(overlaps) == 1
    assert set(overlaps[0]) == {"a", "b"}


# ---------------------------------------------------------------------------
# check_content_overflow
# ---------------------------------------------------------------------------


def test_check_content_overflow_detects_overflow() -> None:
    # Box is far too small for the text even at minimum font size.
    assert check_content_overflow(["A very long line of text"], bbox_width=5.0, bbox_height=5.0) is True


def test_check_content_overflow_width_too_narrow() -> None:
    # Tall box but very narrow — long line overflows horizontally.
    assert check_content_overflow(["ABCDEFGHIJKLMNOPQRSTUVWXYZ"], bbox_width=10.0, bbox_height=500.0) is True


def test_check_content_overflow_height_too_short() -> None:
    # Wide box but only 1 px tall — many lines overflow vertically.
    assert check_content_overflow(["A", "B", "C", "D", "E"], bbox_width=800.0, bbox_height=1.0) is True


def test_check_content_overflow_fits_comfortably() -> None:
    assert check_content_overflow(["Hi"], bbox_width=500.0, bbox_height=100.0) is False


def test_check_content_overflow_empty_lines_never_overflows() -> None:
    assert check_content_overflow([], bbox_width=1.0, bbox_height=1.0) is False


# ---------------------------------------------------------------------------
# render() emits warnings for overlapping slots
# ---------------------------------------------------------------------------


def _two_overlap_svg(tmp_path: Path) -> Path:
    template = tmp_path / "overlap.svg"
    template.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="800" height="480">
          <rect width="800" height="480" fill="white" />
          <text id="slot_a" x="0" y="0"
                data-bbox-width="200" data-bbox-height="100">A</text>
          <text id="slot_b" x="100" y="50"
                data-bbox-width="200" data-bbox-height="100">B</text>
        </svg>""",
        encoding="utf-8",
    )
    return template


def test_render_logs_warning_when_slots_overlap(tmp_path: Path, caplog) -> None:
    template = _two_overlap_svg(tmp_path)
    with caplog.at_level(logging.WARNING, logger="epaper_dashboard_service.adapters.layout.svg"):
        SvgLayoutRenderer().render(template_path=template, blocks=(), width=800, height=480)

    assert any("overlapping" in record.message for record in caplog.records)


def test_render_no_warning_when_slots_do_not_overlap(tmp_path: Path, caplog) -> None:
    template = tmp_path / "no_overlap.svg"
    template.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="800" height="480">
          <rect width="800" height="480" fill="white" />
          <text id="slot_a" x="0" y="0"
                data-bbox-width="200" data-bbox-height="100">A</text>
          <text id="slot_b" x="300" y="200"
                data-bbox-width="200" data-bbox-height="100">B</text>
        </svg>""",
        encoding="utf-8",
    )
    with caplog.at_level(logging.WARNING, logger="epaper_dashboard_service.adapters.layout.svg"):
        SvgLayoutRenderer().render(template_path=template, blocks=(), width=800, height=480)

    overlap_warnings = [r for r in caplog.records if "overlapping" in r.message]
    assert overlap_warnings == []


# ---------------------------------------------------------------------------
# render() emits warnings for content overflow
# ---------------------------------------------------------------------------


def test_render_logs_warning_when_content_overflows(tmp_path: Path, caplog) -> None:
    template = tmp_path / "overflow.svg"
    template.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="800" height="480">
          <rect width="800" height="480" fill="white" />
          <text id="trains" x="10" y="300"
                data-bbox-width="5" data-bbox-height="5">placeholder</text>
        </svg>""",
        encoding="utf-8",
    )
    block = DashboardTextBlock(
        slot="trains",
        lines=("S4 Eichenau", "S4 Pasing", "S4 München Hbf"),
    )
    with caplog.at_level(logging.WARNING, logger="epaper_dashboard_service.adapters.layout.svg"):
        SvgLayoutRenderer().render(
            template_path=template, blocks=(block,), width=800, height=480
        )

    assert any("overflows" in record.message for record in caplog.records)


def test_render_no_warning_when_content_fits(tmp_path: Path, caplog) -> None:
    template = tmp_path / "fits.svg"
    template.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="800" height="480">
          <rect width="800" height="480" fill="white" />
          <text id="trains" x="10" y="300"
                data-bbox-width="600" data-bbox-height="150">placeholder</text>
        </svg>""",
        encoding="utf-8",
    )
    block = DashboardTextBlock(slot="trains", lines=("S4 Eichenau",))
    with caplog.at_level(logging.WARNING, logger="epaper_dashboard_service.adapters.layout.svg"):
        SvgLayoutRenderer().render(
            template_path=template, blocks=(block,), width=800, height=480
        )

    overflow_warnings = [r for r in caplog.records if "overflows" in r.message]
    assert overflow_warnings == []


# ---------------------------------------------------------------------------
# svg_output — intermediate SVG file
# ---------------------------------------------------------------------------

def test_svg_layout_renderer_writes_svg_output_when_path_given(tmp_path: Path) -> None:
    template = _simple_svg(tmp_path)
    svg_out = tmp_path / "out" / "rendered.svg"

    SvgLayoutRenderer().render(
        template_path=template,
        blocks=(DashboardTextBlock(slot="slot", lines=("hello",)),),
        width=200,
        height=100,
        svg_output=svg_out,
    )

    assert svg_out.exists(), "SVG output file must be created"
    content = svg_out.read_text(encoding="utf-8")
    assert "<svg" in content


def test_svg_layout_renderer_no_svg_output_when_path_is_none(tmp_path: Path) -> None:
    template = _simple_svg(tmp_path)

    SvgLayoutRenderer().render(
        template_path=template,
        blocks=(),
        width=200,
        height=100,
        svg_output=None,
    )

    # No stray .svg file should appear in tmp_path (besides the template itself)
    svg_files = [f for f in tmp_path.iterdir() if f.suffix == ".svg" and f != template]
    assert svg_files == []


# ---------------------------------------------------------------------------
# StyledLine — per-line font-size override
# ---------------------------------------------------------------------------

def test_svg_layout_renderer_styled_line_sets_font_size_on_outer_tspan(tmp_path: Path) -> None:
    """StyledLine with font_size must produce an outer tspan carrying font-size."""
    import xml.etree.ElementTree as _ET

    template = _simple_svg(tmp_path)
    departure_spans = (
        TextSpan(text="S4", bold=True),
        TextSpan(text="  10:00"),
    )
    station_line = (TextSpan(text="Eichenau", bold=True),)
    departure_line = StyledLine(spans=departure_spans, font_size=18)
    block = DashboardTextBlock(slot="slot", lines=(station_line, departure_line))

    tree = _ET.parse(template)
    root = tree.getroot()
    SvgLayoutRenderer()._apply_text_block(root, block)

    text_el = next(el for el in root.iter() if el.get("id") == "slot")
    outer_tspans = list(text_el)
    # Second outer tspan corresponds to the departure StyledLine
    assert len(outer_tspans) == 2
    departure_tspan = outer_tspans[1]
    assert departure_tspan.get("font-size") == "18"


def test_svg_layout_renderer_styled_line_inner_spans_have_correct_formatting(tmp_path: Path) -> None:
    """Bold inner spans within a StyledLine must still carry font-weight=bold."""
    import xml.etree.ElementTree as _ET

    template = _simple_svg(tmp_path)
    departure_spans = (
        TextSpan(text="S4", bold=True),
        TextSpan(text="  10:00"),
    )
    departure_line = StyledLine(spans=departure_spans, font_size=18)
    block = DashboardTextBlock(slot="slot", lines=(departure_line,))

    tree = _ET.parse(template)
    root = tree.getroot()
    SvgLayoutRenderer()._apply_text_block(root, block)

    text_el = next(el for el in root.iter() if el.get("id") == "slot")
    outer_tspan = list(text_el)[0]
    inner_tspans = list(outer_tspan)
    bold_inner = [t for t in inner_tspans if t.get("font-weight") == "bold"]
    assert bold_inner, "Bold inner tspan missing in StyledLine"
    assert bold_inner[0].text == "S4"


def test_svg_layout_renderer_styled_line_none_font_size_omits_font_size_attr(tmp_path: Path) -> None:
    """StyledLine with font_size=None must not emit a font-size attribute on the outer tspan."""
    import xml.etree.ElementTree as _ET

    template = _simple_svg(tmp_path)
    departure_line = StyledLine(spans=(TextSpan(text="S4"),), font_size=None)
    block = DashboardTextBlock(slot="slot", lines=(departure_line,))

    tree = _ET.parse(template)
    root = tree.getroot()
    SvgLayoutRenderer()._apply_text_block(root, block)

    text_el = next(el for el in root.iter() if el.get("id") == "slot")
    outer_tspan = list(text_el)[0]
    assert outer_tspan.get("font-size") is None


def test_svg_layout_renderer_styled_line_dy_applied_to_tspan(tmp_path: Path) -> None:
    """StyledLine with dy must set the dy attribute on the outer tspan."""
    import xml.etree.ElementTree as _ET

    template = _simple_svg(tmp_path)
    station_line = StyledLine(spans=(TextSpan(text="Eichenau", bold=True),))
    dep_line = StyledLine(spans=(TextSpan(text="S4  10:00"),), dy="1.6em")
    dest_line = StyledLine(spans=(TextSpan(text="   Leuchtenbergring"),), dy="1.1em")
    block = DashboardTextBlock(slot="slot", lines=(station_line, dep_line, dest_line))

    tree = _ET.parse(template)
    root = tree.getroot()
    SvgLayoutRenderer()._apply_text_block(root, block)

    text_el = next(el for el in root.iter() if el.get("id") == "slot")
    outer_tspans = list(text_el)
    assert outer_tspans[1].get("dy") == "1.6em"
    assert outer_tspans[2].get("dy") == "1.1em"


def test_svg_layout_renderer_plain_rich_line_uses_default_dy(tmp_path: Path) -> None:
    """A plain RichLine (not StyledLine) must fall back to dy=1.2em."""
    import xml.etree.ElementTree as _ET

    template = _simple_svg(tmp_path)
    plain_line = (TextSpan(text="hello"),)
    block = DashboardTextBlock(slot="slot", lines=((TextSpan(text="first"),), plain_line))

    tree = _ET.parse(template)
    root = tree.getroot()
    SvgLayoutRenderer()._apply_text_block(root, block)

    text_el = next(el for el in root.iter() if el.get("id") == "slot")
    outer_tspans = list(text_el)
    assert outer_tspans[1].get("dy") == "1.2em"
