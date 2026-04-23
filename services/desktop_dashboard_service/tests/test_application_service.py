from __future__ import annotations

from pathlib import Path

from PIL import Image

from epaper_dashboard_service.application.service import DashboardApplicationService, PluginRegistry
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
    assert len(result.payload) == 48000
    assert publisher.payload == result.payload
