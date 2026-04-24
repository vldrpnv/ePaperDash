from __future__ import annotations

from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET

import cairosvg
from PIL import Image

from epaper_dashboard_service.domain.models import DashboardTextBlock, RichLine, TextSpan
from epaper_dashboard_service.domain.ports import LayoutRenderer


SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)

# Heuristic constants for proportional sans-serif text measurement.
_CHAR_WIDTH_RATIO = 0.55  # average character width as a fraction of font-size
_LINE_HEIGHT_RATIO = 1.35  # line height (including leading) as a fraction of font-size
_MIN_FONT_SIZE = 8
_MAX_FONT_SIZE = 200


def extract_image_slots(template_path: Path) -> dict[str, dict[str, int]]:
    """Return ``{id: {x, y, width, height}}`` for every ``<image>`` element with an ``id``
    found in the SVG file.  Returns an empty dict when the file does not exist."""
    if not template_path.exists():
        return {}
    tree = ET.parse(template_path)
    root = tree.getroot()
    slots: dict[str, dict[str, int]] = {}
    for element in root.iter():
        if _local_name(element.tag) == "image":
            slot_id = element.get("id")
            if slot_id:
                slots[slot_id] = {
                    "x": int(element.get("x", "0")),
                    "y": int(element.get("y", "0")),
                    "width": int(element.get("width", "0")),
                    "height": int(element.get("height", "0")),
                }
    return slots


class SvgLayoutRenderer(LayoutRenderer):
    def render(self, template_path: Path, blocks: tuple[DashboardTextBlock, ...], width: int, height: int) -> Image.Image:
        tree = ET.parse(template_path)
        root = tree.getroot()

        root.set("width", str(width))
        root.set("height", str(height))
        root.set("viewBox", f"0 0 {width} {height}")

        # Remove <image> placeholder elements (those used as image-slot markers) so they
        # do not appear as broken-image icons in the rasterised output.
        for element in list(root):
            if _local_name(element.tag) == "image" and element.get("id"):
                root.remove(element)

        for block in blocks:
            self._apply_text_block(root, block)

        svg_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        png_bytes = cairosvg.svg2png(bytestring=svg_bytes, output_width=width, output_height=height)
        return Image.open(BytesIO(png_bytes)).convert("L")

    def _find_element_by_id(self, root: ET.Element, element_id: str) -> ET.Element | None:
        for element in root.iter():
            if element.get("id") == element_id:
                return element
        return None

    def _apply_text_block(self, root: ET.Element, block: DashboardTextBlock) -> None:
        element = self._find_element_by_id(root, block.slot)
        if element is None:
            raise ValueError(f"No SVG element found for slot '{block.slot}'")
        if _local_name(element.tag) != "text":
            raise ValueError(f"SVG slot '{block.slot}' must be a <text> element")

        element.text = None
        element[:] = []

        # Auto-size font to fit a declared bounding box when both attributes are present.
        bbox_width = _parse_float(element.get("data-bbox-width"))
        bbox_height = _parse_float(element.get("data-bbox-height"))
        if bbox_width is not None and bbox_height is not None:
            plain_lines = [_line_text(line) for line in block.lines]
            font_size = _fit_font_size(plain_lines, bbox_width, bbox_height)
            element.set("font-size", str(font_size))

        for name, value in block.attributes.items():
            element.set(name, value)

        if not block.lines:
            return

        if len(block.lines) == 1:
            _write_line(element, block.lines[0])
            return

        x = element.get("x", "0")
        for index, line in enumerate(block.lines):
            tspan = ET.SubElement(element, f"{{{SVG_NS}}}tspan")
            tspan.set("x", x)
            if index > 0:
                tspan.set("dy", "1.2em")
            _write_line(tspan, line)


def _write_line(parent: ET.Element, line: str | RichLine) -> None:
    """Write a single line (plain string or sequence of TextSpan) into *parent*."""
    if isinstance(line, str):
        parent.text = line
        return

    # Rich line — emit one inner <tspan> per span with formatting attributes.
    for span in line:
        inner = ET.SubElement(parent, f"{{{SVG_NS}}}tspan")
        if span.bold:
            inner.set("font-weight", "bold")
        if span.strikethrough:
            inner.set("text-decoration", "line-through")
        inner.text = span.text


def _line_text(line: str | RichLine) -> str:
    """Return the plain-text content of a line for measurement purposes."""
    if isinstance(line, str):
        return line
    return "".join(span.text for span in line)


def _fit_font_size(lines: list[str], bbox_width: float, bbox_height: float) -> int:
    """Return the largest integer font-size (px) so that all *lines* fit in the bounding box."""
    if not lines:
        return _MIN_FONT_SIZE
    max_chars = max(len(line) for line in lines)
    num_lines = len(lines)
    if max_chars == 0:
        max_chars = 1
    from_width = bbox_width / (max_chars * _CHAR_WIDTH_RATIO)
    from_height = bbox_height / (num_lines * _LINE_HEIGHT_RATIO)
    return max(_MIN_FONT_SIZE, min(_MAX_FONT_SIZE, int(min(from_width, from_height))))


def _parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _local_name(tag: str) -> str:
    return tag.split("}", 1)[-1]
