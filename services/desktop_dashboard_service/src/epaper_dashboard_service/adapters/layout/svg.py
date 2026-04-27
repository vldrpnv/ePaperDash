from __future__ import annotations

import logging
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET

import cairosvg
from PIL import Image

_log = logging.getLogger(__name__)

from epaper_dashboard_service.domain.models import DashboardTextBlock, RichLine, StyledLine, TextSpan
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


def extract_text_slots(template_path: Path) -> set[str]:
    """Return the set of ``id`` values declared on ``<text>`` elements in the SVG.

    Returns an empty set when the file does not exist.
    """
    if not template_path.exists():
        return set()
    tree = ET.parse(template_path)
    root = tree.getroot()
    slots: set[str] = set()
    for element in root.iter():
        if _local_name(element.tag) == "text":
            slot_id = element.get("id")
            if slot_id:
                slots.add(slot_id)
    return slots


class SvgLayoutRenderer(LayoutRenderer):
    def render(
        self,
        template_path: Path,
        blocks: tuple[DashboardTextBlock, ...],
        width: int,
        height: int,
        cleared_slots: tuple[str, ...] = (),
        svg_output: Path | None = None,
    ) -> Image.Image:
        tree = ET.parse(template_path)
        root = tree.getroot()

        root.set("width", str(width))
        root.set("height", str(height))
        root.set("viewBox", f"0 0 {width} {height}")

        # --- Layout validation (before any mutations) ---
        bboxes = collect_slot_bboxes(root)
        for slot_a, slot_b in check_slot_overlaps(bboxes):
            _log.warning(
                "Layout slots %r and %r have overlapping bounding boxes", slot_a, slot_b
            )
        for block in blocks:
            element = self._find_element_by_id(root, block.slot)
            if element is not None and _local_name(element.tag) == "text":
                bbox_w = _parse_float(element.get("data-bbox-width"))
                bbox_h = _parse_float(element.get("data-bbox-height"))
                if bbox_w is not None and bbox_h is not None:
                    plain_lines = [_line_text(line) for line in block.lines]
                    if check_content_overflow(plain_lines, bbox_w, bbox_h):
                        _log.warning(
                            "Text block for slot %r overflows its bounding box (%.0f×%.0f)",
                            block.slot,
                            bbox_w,
                            bbox_h,
                        )

        # Remove <image> placeholder elements (those used as image-slot markers) so they
        # do not appear as broken-image icons in the rasterised output.
        for element in list(root):
            if _local_name(element.tag) == "image" and element.get("id"):
                root.remove(element)

        for slot in cleared_slots:
            self._clear_text_slot(root, slot)

        for block in blocks:
            self._apply_text_block(root, block)

        # Post-process: replace text-decoration markers with real SVG <line> elements
        # because CairoSVG does not render text-decoration at all.
        for text_el in list(root.iter()):
            if _local_name(text_el.tag) == "text" and text_el.get("id"):
                _inject_strikethrough_lines(root, text_el)

        svg_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        if svg_output is not None:
            svg_output.parent.mkdir(parents=True, exist_ok=True)
            svg_output.write_bytes(svg_bytes)
        png_bytes = cairosvg.svg2png(bytestring=svg_bytes, output_width=width, output_height=height)
        return Image.open(BytesIO(png_bytes)).convert("L")

    def _find_element_by_id(self, root: ET.Element, element_id: str) -> ET.Element | None:
        for element in root.iter():
            if element.get("id") == element_id:
                return element
        return None

    def _clear_text_slot(self, root: ET.Element, slot: str) -> None:
        element = self._find_element_by_id(root, slot)
        if element is None:
            return
        if _local_name(element.tag) != "text":
            return

        element.text = ""
        element[:] = []

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

        if len(block.lines) == 1 and not isinstance(block.lines[0], StyledLine):
            _write_line(element, block.lines[0])
            return

        x = element.get("x", "0")
        for index, line in enumerate(block.lines):
            tspan = ET.SubElement(element, f"{{{SVG_NS}}}tspan")
            tspan.set("x", x)
            if index > 0:
                if isinstance(line, StyledLine) and line.dy is not None:
                    tspan.set("dy", line.dy)
                else:
                    tspan.set("dy", "1.2em")
            if isinstance(line, StyledLine):
                if line.font_size is not None:
                    tspan.set("font-size", str(line.font_size))
                _write_line(tspan, line.spans)
            else:
                _write_line(tspan, line)


def _resolve_em(value: str, font_size: float) -> float:
    """Resolve an SVG/CSS length string like ``'1.5em'`` or ``'20'`` to pixels."""
    if value.endswith("em"):
        f = _parse_float(value[:-2])
        return (f * font_size) if f is not None else 0.0
    f = _parse_float(value)
    return f if f is not None else 0.0


def _inject_strikethrough_lines(root: ET.Element, text_el: ET.Element) -> None:
    """Convert ``text-decoration=line-through`` tspan attributes to SVG ``<line>`` elements.

    CairoSVG does not render the CSS ``text-decoration`` property (neither via
    ``style=`` nor as a presentation attribute).  This function scans *text_el*
    for struck spans, removes the attribute, and appends a ``<line>`` element to
    *root* at the estimated screen position of each struck span.
    """
    text_x = _parse_float(text_el.get("x")) or 0.0
    text_y = _parse_float(text_el.get("y")) or 0.0
    text_font_size = _parse_float(text_el.get("font-size")) or 16.0

    def _process_spans(
        parent: ET.Element,
        font_size: float,
        start_x: float,
        baseline_y: float,
    ) -> None:
        current_x = start_x
        for child in list(parent):
            if _local_name(child.tag) != "tspan":
                continue
            span_text = child.text or ""
            child_font_size = _parse_float(child.get("font-size")) or font_size
            is_bold = child.get("font-weight") == "bold"
            char_w = child_font_size * _CHAR_WIDTH_RATIO * (1.1 if is_bold else 1.0)
            span_width = len(span_text) * char_w
            if child.get("text-decoration") == "line-through":
                del child.attrib["text-decoration"]
                # Strike sits at ~35 % of font height above the baseline.
                strike_y = baseline_y - child_font_size * 0.35
                line_el = ET.Element(f"{{{SVG_NS}}}line")
                line_el.set("x1", f"{current_x:.1f}")
                line_el.set("y1", f"{strike_y:.1f}")
                line_el.set("x2", f"{current_x + span_width:.1f}")
                line_el.set("y2", f"{strike_y:.1f}")
                line_el.set("stroke", "black")
                line_el.set("stroke-width", "1.5")
                root.append(line_el)
            current_x += span_width

    # Detect layout mode: outer tspan wrappers (multi-line, each has x=) vs direct
    # inner spans (single-line shortcut, no x= on children).
    has_outer_tspans = any(
        _local_name(child.tag) == "tspan" and child.get("x") is not None
        for child in text_el
    )
    if has_outer_tspans:
        current_y = text_y
        for outer in text_el:
            if _local_name(outer.tag) != "tspan":
                continue
            outer_font_size = _parse_float(outer.get("font-size")) or text_font_size
            dy_str = outer.get("dy")
            if dy_str:
                current_y += _resolve_em(dy_str, outer_font_size)
            line_x = _parse_float(outer.get("x")) or text_x
            _process_spans(outer, outer_font_size, line_x, current_y)
    else:
        _process_spans(text_el, text_font_size, text_x, text_y)


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
            # Mark for post-processing: _inject_strikethrough_lines replaces this
            # attribute with a real SVG <line> element because CairoSVG does not
            # render text-decoration (neither as CSS nor as a presentation attribute).
            inner.set("text-decoration", "line-through")
        inner.text = span.text


def _line_text(line: str | RichLine | StyledLine) -> str:
    """Return the plain-text content of a line for measurement purposes."""
    if isinstance(line, str):
        return line
    if isinstance(line, StyledLine):
        return "".join(span.text for span in line.spans)
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


def collect_slot_bboxes(root: ET.Element) -> dict[str, tuple[float, float, float, float]]:
    """Return ``{id: (x, y, width, height)}`` for every slot with a known bounding box.

    Covered cases:

    * ``<text>`` elements that carry both ``data-bbox-width`` and ``data-bbox-height``.
    * ``<image>`` elements with explicit ``width`` and ``height``.
    """
    bboxes: dict[str, tuple[float, float, float, float]] = {}
    for element in root.iter():
        tag = _local_name(element.tag)
        slot_id = element.get("id")
        if not slot_id:
            continue
        if tag == "text":
            x = _parse_float(element.get("x")) or 0.0
            y = _parse_float(element.get("y")) or 0.0
            w = _parse_float(element.get("data-bbox-width"))
            h = _parse_float(element.get("data-bbox-height"))
            if w is not None and h is not None:
                bboxes[slot_id] = (x, y, w, h)
        elif tag == "image":
            x = _parse_float(element.get("x")) or 0.0
            y = _parse_float(element.get("y")) or 0.0
            w = _parse_float(element.get("width")) or 0.0
            h = _parse_float(element.get("height")) or 0.0
            if w > 0 and h > 0:
                bboxes[slot_id] = (x, y, w, h)
    return bboxes


def check_slot_overlaps(
    bboxes: dict[str, tuple[float, float, float, float]],
) -> list[tuple[str, str]]:
    """Return a list of ``(id_a, id_b)`` pairs whose bounding boxes share area."""
    ids = list(bboxes)
    overlapping: list[tuple[str, str]] = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            if _rects_overlap(bboxes[ids[i]], bboxes[ids[j]]):
                overlapping.append((ids[i], ids[j]))
    return overlapping


def check_content_overflow(lines: list[str], bbox_width: float, bbox_height: float) -> bool:
    """Return ``True`` when the text cannot fit the bounding box even at ``_MIN_FONT_SIZE``.

    Uses the same heuristic character-width and line-height ratios as ``_fit_font_size``.
    """
    if not lines:
        return False
    max_chars = max((len(line) for line in lines), default=1) or 1
    num_lines = len(lines)
    est_width = max_chars * _MIN_FONT_SIZE * _CHAR_WIDTH_RATIO
    est_height = num_lines * _MIN_FONT_SIZE * _LINE_HEIGHT_RATIO
    return est_width > bbox_width or est_height > bbox_height


def _rects_overlap(
    r1: tuple[float, float, float, float],
    r2: tuple[float, float, float, float],
) -> bool:
    """Return ``True`` if two ``(x, y, w, h)`` rectangles share any area."""
    x1, y1, w1, h1 = r1
    x2, y2, w2, h2 = r2
    return not (x1 + w1 <= x2 or x2 + w2 <= x1 or y1 + h1 <= y2 or y2 + h2 <= y1)


def _parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _local_name(tag: str) -> str:
    return tag.split("}", 1)[-1]
