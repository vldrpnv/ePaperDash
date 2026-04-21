from __future__ import annotations

from pathlib import Path

from epaper_dashboard_service.adapters.layout.svg import SvgLayoutRenderer
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
