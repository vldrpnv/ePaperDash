import os
from pathlib import Path
from datetime import datetime
from PIL import Image
import io


def generate_preview(config_filepath: Path | str) -> bytes:
    os.environ["DASHBOARD_CONFIG_PATH"] = str(config_filepath)

    from epaper_dashboard_service.application.config import load_configuration
    from epaper_dashboard_service.application.service import _composite_image_placements
    from epaper_dashboard_service.adapters.layout.svg import (
        SvgLayoutRenderer,
        extract_text_slots,
        extract_image_slots,
    )
    from epaper_dashboard_service.domain.ports import SourcePlugin, RendererPlugin
    from epaper_dashboard_service.domain.models import (
        DashboardTextBlock,
        ImagePlacement,
        PanelDefinition,
    )
    import dataclasses

    config = load_configuration(Path(config_filepath))

    import typing

    class DummySource(SourcePlugin):
        @property
        def name(self) -> str:
            return "dummy"

        def fetch(self, config: dict) -> typing.Any:
            return {"dummy": "data"}

    class DummyRenderer(RendererPlugin):
        @property
        def name(self) -> str:
            return "dummy"

        @property
        def supported_type(self):
            return dict

        def render(self, data, panel_definition):
            return [DashboardTextBlock(slot=panel_definition.slot, lines=("Preview",))]

    text_blocks: list[DashboardTextBlock] = []
    image_placements: list[ImagePlacement] = []

    # Handle Profiles vs Legacy
    resolved_template_path = config.layout.template
    panels = config.panels

    if hasattr(config, "profiles") and config.profiles:
        # Sort profiles by start time, descending (e.g., "21:00", "09:00", "00:00")
        local_now = datetime.now()
        sorted_profiles = sorted(
            config.profiles, key=lambda p: p.start_time, reverse=True
        )
        current_time_str = local_now.strftime("%H:%M")

        active_profile = sorted_profiles[0]  # fallback
        for profile in sorted_profiles:
            if current_time_str >= profile.start_time:
                active_profile = profile
                break

        resolved_template_path = active_profile.template
        sources_by_id = {s.id: s for s in config.sources}
        panels_list = []
        for profile_panel in active_profile.panels:
            source_def = sources_by_id.get(profile_panel.source_id)
            if source_def:
                panels_list.append(
                    PanelDefinition(
                        source=source_def.source,
                        renderer=profile_panel.renderer,
                        slot=profile_panel.slot,
                        source_config=source_def.source_config,
                        renderer_config=profile_panel.renderer_config,
                    )
                )
        panels = tuple(panels_list)

    template_path = Path(resolved_template_path)

    if not template_path.exists():
        # Fallback empty image
        img = Image.new("RGB", (config.layout.width, config.layout.height), "white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    svg_image_slots = extract_image_slots(template_path)
    svg_text_slots = extract_text_slots(template_path)

    for panel in panels:
        if panel.slot in svg_image_slots:
            panel = dataclasses.replace(
                panel,
                renderer_config={
                    **panel.renderer_config,
                    **svg_image_slots[panel.slot],
                },
            )
        # Use dummy for everything
        renderer = DummyRenderer()
        for block in renderer.render({"dummy": "data"}, panel):
            text_blocks.append(block)

    if "last_update" in svg_text_slots:
        local_now = datetime.now().astimezone()
        timestamp = local_now.strftime("%Y-%m-%d %H:%M:%S %z")
        text_blocks.append(
            DashboardTextBlock(
                slot="last_update",
                lines=(f"Preview: {timestamp}",),
            )
        )

    layout_renderer = SvgLayoutRenderer()
    image = layout_renderer.render(
        template_path=template_path,
        blocks=tuple(text_blocks),
        width=config.layout.width,
        height=config.layout.height,
        cleared_slots=tuple(),
        svg_output=None,
    )

    image = _composite_image_placements(image, tuple(image_placements))

    preview_img = image.convert("RGB")
    buf = io.BytesIO()
    preview_img.save(buf, format="PNG")
    return buf.getvalue()
