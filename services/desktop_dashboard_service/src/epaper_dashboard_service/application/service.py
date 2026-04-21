from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from epaper_dashboard_service.domain.models import DashboardConfiguration, DashboardTextBlock
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

    def generate_and_publish(self, configuration: DashboardConfiguration) -> DashboardBuildResult:
        blocks: list[DashboardTextBlock] = []
        for panel in configuration.panels:
            source = self._registry.get_source(panel.source)
            renderer = self._registry.get_renderer(panel.renderer)
            data = source.fetch(panel.source_config)
            if not isinstance(data, renderer.supported_type):
                raise TypeError(
                    f"Renderer '{renderer.name}' cannot render '{type(data).__name__}' from source '{source.name}'"
                )
            blocks.extend(renderer.render(data, panel))

        image = self._layout_renderer.render(
            template_path=Path(configuration.layout.template),
            blocks=tuple(blocks),
            width=configuration.layout.width,
            height=configuration.layout.height,
        )
        payload = _encode_to_epaper_payload(image)

        if configuration.layout.preview_output:
            preview_path = Path(configuration.layout.preview_output)
            preview_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(preview_path)

        self._publisher.publish(payload)
        return DashboardBuildResult(image=image, payload=payload)


def _encode_to_epaper_payload(image: Image.Image) -> bytes:
    monochrome = image.convert("1")
    return monochrome.tobytes()
