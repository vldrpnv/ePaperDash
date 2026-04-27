from __future__ import annotations

from pathlib import Path
import re

from PIL import Image
import pytest

from epaper_dashboard_service.adapters.layout.svg import SvgLayoutRenderer
from epaper_dashboard_service.adapters.rendering.image import ImagePlacementRenderer
from epaper_dashboard_service.adapters.sources.random_image import RandomImageSourcePlugin
from epaper_dashboard_service.application.service import DashboardApplicationService, PluginRegistry, _encode_to_epaper_payload
from epaper_dashboard_service.domain.errors import SourceUnavailableError
from epaper_dashboard_service.domain.models import DashboardConfiguration, LayoutConfig, MqttConfig, PanelDefinition
from epaper_dashboard_service.domain.ports import DashboardPublisher, LayoutRenderer, RendererPlugin, SourcePlugin


class FakeSource(SourcePlugin):
    name = "calendar"

    def fetch(self, config: dict[str, object]) -> object:
        return config["value"]


class FakeRenderer(RendererPlugin):
    name = "calendar_text"
    supported_type = str

    def render(self, data: object, panel: PanelDefinition):
        from epaper_dashboard_service.domain.models import DashboardTextBlock

        return (DashboardTextBlock(slot=panel.slot, lines=(str(data),)),)


class FakeLayoutRenderer(LayoutRenderer):
    def __init__(self) -> None:
        self.blocks = ()
        self.cleared_slots = ()

    def render(self, template_path: Path, blocks, width: int, height: int, cleared_slots=(), svg_output=None) -> Image.Image:
        self.blocks = blocks
        self.cleared_slots = cleared_slots
        return Image.new("L", (width, height), color=255)


class FakePublisher(DashboardPublisher):
    def __init__(self) -> None:
        self.payload = b""

    def publish(self, payload: bytes) -> None:
        self.payload = payload


def test_application_service_renders_and_publishes_payload() -> None:
    layout_renderer = FakeLayoutRenderer()
    publisher = FakePublisher()
    service = DashboardApplicationService(
        registry=PluginRegistry(sources=(FakeSource(),), renderers=(FakeRenderer(),)),
        layout_renderer=layout_renderer,
        publisher=publisher,
    )
    configuration = DashboardConfiguration(
        layout=LayoutConfig(template="/tmp/layout.svg", width=800, height=480),
        mqtt=MqttConfig(host="localhost", port=1883, topic="epaper/image"),
        panels=(
            PanelDefinition(
                source="calendar",
                renderer="calendar_text",
                slot="calendar",
                source_config={"value": "Tuesday"},
                renderer_config={},
            ),
        ),
    )

    result = service.generate_and_publish(configuration)

    assert layout_renderer.blocks[0].lines == ("Tuesday",)
    assert len(result.payload) == 800 * 480 // 8  # 48 000 bytes
    assert publisher.payload == result.payload


def test_epaper_payload_inverts_bits_for_firmware_convention() -> None:
    """Firmware expects white=0, black=1; PIL tobytes() produces white=1, black=0."""
    # All-white image: after inversion every byte should be 0x00
    white_image = Image.new("L", (800, 480), color=255)
    payload = _encode_to_epaper_payload(white_image)
    assert all(b == 0x00 for b in payload), "All-white image should encode to all-zero bytes (white=0)"

    # All-black image: after inversion every byte should be 0xFF
    black_image = Image.new("L", (800, 480), color=0)
    payload = _encode_to_epaper_payload(black_image)
    assert all(b == 0xFF for b in payload), "All-black image should encode to all-0xFF bytes (black=1)"


def test_application_service_generate_does_not_publish() -> None:
    publisher = FakePublisher()
    service = DashboardApplicationService(
        registry=PluginRegistry(sources=(FakeSource(),), renderers=(FakeRenderer(),)),
        layout_renderer=FakeLayoutRenderer(),
        publisher=publisher,
    )
    configuration = DashboardConfiguration(
        layout=LayoutConfig(template="/tmp/layout.svg", width=800, height=480),
        mqtt=MqttConfig(host="localhost", port=1883, topic="epaper/image"),
        panels=(
            PanelDefinition(
                source="calendar",
                renderer="calendar_text",
                slot="calendar",
                source_config={"value": "Tuesday"},
                renderer_config={},
            ),
        ),
    )

    service.generate(configuration)

    assert publisher.payload == b"", "generate() must not publish"


def test_application_service_composites_random_image_panel(tmp_path: Path) -> None:
    """The service must composite an ImagePlacement from the random_image panel onto the output."""
    # Create a small all-black image in the pool directory
    pool_dir = tmp_path / "pool"
    pool_dir.mkdir()
    black_img = Image.new("RGB", (50, 30), color=0)
    black_img.save(pool_dir / "photo.png")

    publisher = FakePublisher()
    service = DashboardApplicationService(
        registry=PluginRegistry(
            sources=(FakeSource(), RandomImageSourcePlugin()),
            renderers=(FakeRenderer(), ImagePlacementRenderer()),
        ),
        layout_renderer=FakeLayoutRenderer(),
        publisher=publisher,
    )
    # Image box: top-left corner at (0, 0), 80x60 — large enough to verify compositing
    configuration = DashboardConfiguration(
        layout=LayoutConfig(template="/tmp/layout.svg", width=800, height=480),
        mqtt=MqttConfig(host="localhost", port=1883, topic="epaper/image"),
        panels=(
            PanelDefinition(
                source="calendar",
                renderer="calendar_text",
                slot="calendar",
                source_config={"value": "Tuesday"},
                renderer_config={},
            ),
            PanelDefinition(
                source="random_image",
                renderer="random_image",
                slot="image_pool",
                source_config={"directory": str(pool_dir)},
                renderer_config={"x": 0, "y": 0, "width": 80, "height": 60},
            ),
        ),
    )

    result = service.generate(configuration)

    # The composited image should still be 800x480
    assert result.image.size == (800, 480)
    # The top-left 80x60 region should contain the (black) image that was pasted;
    # at least the centre pixel of the box should be black (grayscale < 128).
    centre_pixel = result.image.getpixel((40, 30))
    assert centre_pixel < 128, (
        "Centre of the composited image box should be dark (black image was pasted there)"
    )


def test_application_service_reads_image_slot_geometry_from_svg(tmp_path: Path) -> None:
    """When <image id="..."> is present in the SVG template, its geometry must drive placement
    even when renderer_config carries no x/y/width/height values."""
    # SVG declares a 80x60 box at (50, 50)
    template = tmp_path / "layout.svg"
    template.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="800" height="480">
          <rect width="800" height="480" fill="white" />
          <image id="image_pool" x="50" y="50" width="80" height="60" />
        </svg>""",
        encoding="utf-8",
    )

    pool_dir = tmp_path / "pool"
    pool_dir.mkdir()
    black_img = Image.new("RGB", (50, 30), color=0)
    black_img.save(pool_dir / "photo.png")

    publisher = FakePublisher()
    service = DashboardApplicationService(
        registry=PluginRegistry(
            sources=(RandomImageSourcePlugin(),),
            renderers=(ImagePlacementRenderer(),),
        ),
        layout_renderer=SvgLayoutRenderer(),
        publisher=publisher,
    )
    configuration = DashboardConfiguration(
        layout=LayoutConfig(template=str(template), width=800, height=480),
        mqtt=MqttConfig(host="localhost", port=1883, topic="epaper/image"),
        panels=(
            PanelDefinition(
                source="random_image",
                renderer="random_image",
                slot="image_pool",
                source_config={"directory": str(pool_dir)},
                renderer_config={},  # no x/y/width/height — must come from SVG
            ),
        ),
    )

    result = service.generate(configuration)

    assert result.image.size == (800, 480)
    # Centre of the 80x60 box at (50, 50) is (90, 80); the black image should be there.
    centre_pixel = result.image.getpixel((90, 80))
    assert centre_pixel < 128, "Centre of SVG-declared image box should be dark"


class UnavailableSource(SourcePlugin):
    name = "unavailable"

    def fetch(self, config: dict[str, object]) -> object:
        raise SourceUnavailableError("upstream timeout")


def test_application_service_skips_unavailable_source_and_clears_slot() -> None:
    layout_renderer = FakeLayoutRenderer()
    service = DashboardApplicationService(
        registry=PluginRegistry(
            sources=(FakeSource(), UnavailableSource()),
            renderers=(FakeRenderer(),),
        ),
        layout_renderer=layout_renderer,
        publisher=FakePublisher(),
    )
    configuration = DashboardConfiguration(
        layout=LayoutConfig(template="/tmp/layout.svg", width=800, height=480),
        mqtt=MqttConfig(host="localhost", port=1883, topic="epaper/image"),
        panels=(
            PanelDefinition(
                source="calendar",
                renderer="calendar_text",
                slot="calendar",
                source_config={"value": "Tuesday"},
                renderer_config={},
            ),
            PanelDefinition(
                source="unavailable",
                renderer="calendar_text",
                slot="weather",
                source_config={},
                renderer_config={},
            ),
        ),
    )

    result = service.generate(configuration)

    assert len(result.payload) == 800 * 480 // 8
    assert tuple(block.slot for block in layout_renderer.blocks) == ("calendar",)
    assert layout_renderer.cleared_slots == ("weather",)


def test_application_service_adds_last_update_block_when_slot_exists(tmp_path: Path) -> None:
    template = tmp_path / "layout.svg"
    template.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="800" height="480">
          <rect width="800" height="480" fill="white" />
          <text id="last_update" x="8" y="476" font-size="10" />
        </svg>""",
        encoding="utf-8",
    )

    layout_renderer = FakeLayoutRenderer()
    service = DashboardApplicationService(
        registry=PluginRegistry(sources=(), renderers=()),
        layout_renderer=layout_renderer,
        publisher=FakePublisher(),
    )
    configuration = DashboardConfiguration(
        layout=LayoutConfig(template=str(template), width=800, height=480),
        mqtt=MqttConfig(host="localhost", port=1883, topic="epaper/image"),
        panels=(),
    )

    service.generate(configuration)

    last_update_blocks = [block for block in layout_renderer.blocks if block.slot == "last_update"]
    assert len(last_update_blocks) == 1
    assert len(last_update_blocks[0].lines) == 1
    assert isinstance(last_update_blocks[0].lines[0], str)
    assert re.match(
        r"^Last update: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} [+-]\d{4}$",
        last_update_blocks[0].lines[0],
    )


def test_application_service_skips_last_update_when_slot_missing(tmp_path: Path) -> None:
    template = tmp_path / "layout.svg"
    template.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="800" height="480">
          <rect width="800" height="480" fill="white" />
          <text id="calendar" x="50" y="110" />
        </svg>""",
        encoding="utf-8",
    )

    layout_renderer = FakeLayoutRenderer()
    service = DashboardApplicationService(
        registry=PluginRegistry(sources=(), renderers=()),
        layout_renderer=layout_renderer,
        publisher=FakePublisher(),
    )
    configuration = DashboardConfiguration(
        layout=LayoutConfig(template=str(template), width=800, height=480),
        mqtt=MqttConfig(host="localhost", port=1883, topic="epaper/image"),
        panels=(),
    )

    service.generate(configuration)

    assert all(block.slot != "last_update" for block in layout_renderer.blocks)

