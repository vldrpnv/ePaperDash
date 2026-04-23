from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from epaper_dashboard_service.domain.models import (
    DashboardConfiguration,
    DashboardTextBlock,
    ImagePlacement,
)
from epaper_dashboard_service.domain.ports import DashboardPublisher, LayoutRenderer, RendererPlugin, SourcePlugin


class PluginRegistry:
    def __init__(self, sources: tuple[SourcePlugin, ...], renderers: tuple[RendererPlugin, ...]) -> None:
        self._sources = {plugin.name: plugin for plugin in sources}
        self._renderers = {plugin.name: plugin for plugin in renderers}

    def get_source(self, name: str) -> SourcePlugin:
        try:
            return self._sources[name]
        except KeyError as error:
            raise LookupError(f"Unknown source plugin: {name}") from error

    def get_renderer(self, name: str) -> RendererPlugin:
        try:
            return self._renderers[name]
        except KeyError as error:
            raise LookupError(f"Unknown renderer plugin: {name}") from error


@dataclass(frozen=True)
class DashboardBuildResult:
    image: Image.Image
    payload: bytes


class DashboardApplicationService:
    def __init__(self, registry: PluginRegistry, layout_renderer: LayoutRenderer, publisher: DashboardPublisher) -> None:
        self._registry = registry
        self._layout_renderer = layout_renderer
        self._publisher = publisher

    def generate(self, configuration: DashboardConfiguration) -> DashboardBuildResult:
        """Render the dashboard and return the result without publishing."""
        text_blocks: list[DashboardTextBlock] = []
        image_placements: list[ImagePlacement] = []

        for panel in configuration.panels:
            source = self._registry.get_source(panel.source)
            renderer = self._registry.get_renderer(panel.renderer)
            data = source.fetch(panel.source_config)
            if not isinstance(data, renderer.supported_type):
                raise TypeError(
                    f"Renderer '{renderer.name}' cannot render '{type(data).__name__}' from source '{source.name}'"
                )
            for block in renderer.render(data, panel):
                if isinstance(block, ImagePlacement):
                    image_placements.append(block)
                else:
                    text_blocks.append(block)

        image = self._layout_renderer.render(
            template_path=Path(configuration.layout.template),
            blocks=tuple(text_blocks),
            width=configuration.layout.width,
            height=configuration.layout.height,
        )

        image = _composite_image_placements(image, tuple(image_placements))
        payload = _encode_to_epaper_payload(image)

        if configuration.layout.preview_output:
            preview_path = Path(configuration.layout.preview_output)
            preview_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(preview_path)

        return DashboardBuildResult(image=image, payload=payload)

    def publish(self, payload: bytes) -> None:
        """Publish a payload directly."""
        self._publisher.publish(payload)

    def generate_and_publish(self, configuration: DashboardConfiguration) -> DashboardBuildResult:
        result = self.generate(configuration)
        self._publisher.publish(result.payload)
        return result


def _composite_image_placements(base: Image.Image, placements: tuple[ImagePlacement, ...]) -> Image.Image:
    if not placements:
        return base
    result = base.copy()
    for placement in placements:
        result.paste(placement.image, (placement.x, placement.y))
    return result


def _encode_to_epaper_payload(image: Image.Image) -> bytes:
    expected_width = 800
    expected_height = 480

    if image.size != (expected_width, expected_height):
        raise ValueError(
            "E-paper payload requires an image of "
            f"{expected_width}x{expected_height} pixels, got {image.width}x{image.height}"
        )

    if image.width % 8 != 0:
        raise ValueError(
            f"E-paper payload width must be divisible by 8 for 1-bpp packing, got {image.width}"
        )

    monochrome = image.convert("1")
    # PIL "1" mode tobytes() packs white=1, black=0.
    # The firmware requires white=0, black=1, so invert all bytes.
    payload = bytes(b ^ 0xFF for b in monochrome.tobytes())
    expected_payload_size = expected_width * expected_height // 8

    if len(payload) != expected_payload_size:
        raise ValueError(
            "E-paper payload must be exactly "
            f"{expected_payload_size} bytes for a {expected_width}x{expected_height} 1-bpp image, "
            f"got {len(payload)} bytes"
        )

    return payload
