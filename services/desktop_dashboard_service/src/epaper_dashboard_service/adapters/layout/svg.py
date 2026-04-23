from __future__ import annotations

from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET

import cairosvg
from PIL import Image

from epaper_dashboard_service.domain.models import DashboardTextBlock
from epaper_dashboard_service.domain.ports import LayoutRenderer


SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)


class SvgLayoutRenderer(LayoutRenderer):
    def render(self, template_path: Path, blocks: tuple[DashboardTextBlock, ...], width: int, height: int) -> Image.Image:
        tree = ET.parse(template_path)
        root = tree.getroot()

        root.set("width", str(width))
        root.set("height", str(height))
        root.set("viewBox", f"0 0 {width} {height}")

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
        for name, value in block.attributes.items():
            element.set(name, value)

        if not block.lines:
            return
        if len(block.lines) == 1:
            element.text = block.lines[0]
            return

        x = element.get("x", "0")
        for index, line in enumerate(block.lines):
            tspan = ET.SubElement(element, f"{{{SVG_NS}}}tspan")
            tspan.set("x", x)
            if index > 0:
                tspan.set("dy", "1.2em")
            tspan.text = line


def _local_name(tag: str) -> str:
    return tag.split("}", 1)[-1]
