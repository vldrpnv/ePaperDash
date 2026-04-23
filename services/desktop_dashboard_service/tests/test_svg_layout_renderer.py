from __future__ import annotations

from pathlib import Path

from epaper_dashboard_service.adapters.layout.svg import SvgLayoutRenderer, _fit_font_size
from epaper_dashboard_service.domain.models import DashboardTextBlock, TextSpan


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

    tree = _ET.parse(template)
    root = tree.getroot()
    SvgLayoutRenderer()._apply_text_block(root, block)

    text_el = next(el for el in root.iter() if el.get("id") == "slot")
    struck = [t for t in text_el if t.get("text-decoration") == "line-through"]
    assert len(struck) == 1
    assert "10:15" in struck[0].text


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
