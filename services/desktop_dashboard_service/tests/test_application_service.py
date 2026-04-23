from __future__ import annotations

from pathlib import Path

from PIL import Image
import pytest

from epaper_dashboard_service.adapters.rendering.image import ImagePlacementRenderer
from epaper_dashboard_service.adapters.sources.random_image import RandomImageSourcePlugin
from epaper_dashboard_service.application.service import DashboardApplicationService, PluginRegistry, _encode_to_epaper_payload
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

    def render(self, template_path: Path, blocks, width: int, height: int) -> Image.Image:
        self.blocks = blocks
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

