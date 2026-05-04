from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image

from epaper_dashboard_service.adapters.layout.svg import extract_image_slots, extract_text_slots
from epaper_dashboard_service.domain.errors import SourceUnavailableError
from epaper_dashboard_service.domain.models import (
    DashboardConfiguration,
    DashboardTextBlock,
    ImagePlacement,
    PanelDefinition,
    ProfileDefinition,
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

    def _get_active_profile(self, profiles: tuple[ProfileDefinition, ...], local_now: datetime) -> ProfileDefinition | None:
        if not profiles:
            return None

        # Sort profiles by start time, descending (e.g., "21:00", "09:00", "00:00")
        sorted_profiles = sorted(profiles, key=lambda p: p.start_time, reverse=True)
        current_time_str = local_now.strftime("%H:%M")

        # Find the first profile that started before or at the current time
        for profile in sorted_profiles:
            if current_time_str >= profile.start_time:
                return profile

        # If no profile started before the current time, wrap around to the latest one
        # (e.g. current time is 01:00, profiles are 09:00 and 21:00, active is 21:00)
        return sorted_profiles[0]

    def _resolve_panels(self, configuration: DashboardConfiguration, local_now: datetime) -> tuple[tuple[PanelDefinition, ...], str | None]:
        # Legacy case: direct panels configured
        if not configuration.profiles:
            return configuration.panels, configuration.layout.template

        # Profile case
        active_profile = self._get_active_profile(configuration.profiles, local_now)
        if not active_profile:
            return tuple(), None

        sources_by_id = {s.id: s for s in configuration.sources}
        panels = []

        for profile_panel in active_profile.panels:
            source_def = sources_by_id.get(profile_panel.source_id)
            if not source_def:
                raise ValueError(f"Profile '{active_profile.id}' references unknown source '{profile_panel.source_id}'")

            panels.append(
                PanelDefinition(
                    source=source_def.source,
                    renderer=profile_panel.renderer,
                    slot=profile_panel.slot,
                    source_config=source_def.source_config,
                    renderer_config=profile_panel.renderer_config,
                )
            )

        return tuple(panels), active_profile.template

    def generate(self, configuration: DashboardConfiguration) -> DashboardBuildResult:
        """Render the dashboard and return the result without publishing."""
        text_blocks: list[DashboardTextBlock] = []
        image_placements: list[ImagePlacement] = []
        cleared_slots: list[str] = []

        local_now = datetime.now().astimezone()

        panels, template_path_str = self._resolve_panels(configuration, local_now)
        if not template_path_str:
            raise ValueError("No valid layout template could be resolved")

        template_path = Path(template_path_str)

        # Read image-slot geometry declared in the SVG template.  These values are merged
        # into renderer_config so that image panels can be positioned purely from the SVG.
        svg_image_slots = extract_image_slots(template_path)
        svg_text_slots = extract_text_slots(template_path)

        for panel in panels:
            # If the SVG defines geometry for this slot, merge it into renderer_config.
            # SVG geometry takes precedence over any matching keys in the TOML config.
            if panel.slot in svg_image_slots:
                panel = dataclasses.replace(
                    panel,
                    renderer_config={**panel.renderer_config, **svg_image_slots[panel.slot]},
                )
            source = self._registry.get_source(panel.source)
            renderer = self._registry.get_renderer(panel.renderer)
            try:
                data = source.fetch(panel.source_config)
            except SourceUnavailableError:
                cleared_slots.append(panel.slot)
                continue
            if not isinstance(data, renderer.supported_type):
                raise TypeError(
                    f"Renderer '{renderer.name}' cannot render '{type(data).__name__}' from source '{source.name}'"
                )
            for block in renderer.render(data, panel):
                if isinstance(block, ImagePlacement):
                    image_placements.append(block)
                else:
                    text_blocks.append(block)

        if "last_update" in svg_text_slots:
            timestamp = local_now.strftime("%Y-%m-%d %H:%M:%S %z")
            text_blocks.append(
                DashboardTextBlock(
                    slot="last_update",
                    lines=(f"Last update: {timestamp}",),
                )
            )

        svg_output: Path | None = None
        if configuration.layout.preview_output:
            svg_output = Path(configuration.layout.preview_output).with_suffix(".svg")

        image = self._layout_renderer.render(
            template_path=template_path,
            blocks=tuple(text_blocks),
            width=configuration.layout.width,
            height=configuration.layout.height,
            cleared_slots=tuple(cleared_slots),
            svg_output=svg_output,
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
