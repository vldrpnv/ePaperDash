from __future__ import annotations

from pathlib import Path

from epaper_dashboard_service.adapters.layout.svg import SvgLayoutRenderer, extract_image_slots
from epaper_dashboard_service.domain.models import DashboardTextBlock


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

