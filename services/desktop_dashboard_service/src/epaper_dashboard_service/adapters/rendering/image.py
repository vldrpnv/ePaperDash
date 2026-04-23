from __future__ import annotations

from PIL import Image

from epaper_dashboard_service.domain.models import ImagePlacement, PanelDefinition, RandomImageData
from epaper_dashboard_service.domain.ports import RendererPlugin


class ImagePlacementRenderer(RendererPlugin):
    """Resizes a RandomImageData image to fit a configured box and returns an ImagePlacement."""

    name = "random_image"
    supported_type = RandomImageData

    def render(self, data: RandomImageData, panel: PanelDefinition) -> tuple[ImagePlacement, ...]:
        if data.image is None:
            return ()

        cfg = panel.renderer_config
        x = int(cfg.get("x", 0))
        y = int(cfg.get("y", 0))
        width = int(cfg.get("width", 300))
        height = int(cfg.get("height", 200))

        fitted = _resize_to_fit(data.image, width, height)
        return (ImagePlacement(image=fitted, x=x, y=y),)


def _resize_to_fit(image: Image.Image, width: int, height: int) -> Image.Image:
    """Return a grayscale (L) image of exactly (width, height) with the source resized
    proportionally to fit inside the box, centred on a white background."""
    canvas = Image.new("L", (width, height), 255)
    gray = image.convert("L")
    gray.thumbnail((width, height), Image.LANCZOS)
    x_offset = (width - gray.width) // 2
    y_offset = (height - gray.height) // 2
    canvas.paste(gray, (x_offset, y_offset))
    return canvas
