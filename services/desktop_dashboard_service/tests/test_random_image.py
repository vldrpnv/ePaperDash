from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from epaper_dashboard_service.adapters.rendering.image import ImagePlacementRenderer, _resize_to_fit
from epaper_dashboard_service.adapters.sources.random_image import RandomImageSourcePlugin
from epaper_dashboard_service.domain.models import ImagePlacement, PanelDefinition, RandomImageData


# ---------------------------------------------------------------------------
# RandomImageSourcePlugin
# ---------------------------------------------------------------------------

def test_random_image_source_returns_none_for_empty_directory(tmp_path: Path) -> None:
    plugin = RandomImageSourcePlugin()
    result = plugin.fetch({"directory": str(tmp_path)})
    assert isinstance(result, RandomImageData)
    assert result.image is None


def test_random_image_source_returns_image_from_directory(tmp_path: Path) -> None:
    img = Image.new("RGB", (100, 80), color=(128, 64, 200))
    img.save(tmp_path / "sample.png")

    plugin = RandomImageSourcePlugin()
    result = plugin.fetch({"directory": str(tmp_path)})

    assert isinstance(result, RandomImageData)
    assert result.image is not None
    assert result.image.size == (100, 80)


def test_random_image_source_raises_for_missing_directory() -> None:
    plugin = RandomImageSourcePlugin()
    with pytest.raises(ValueError, match="directory does not exist"):
        plugin.fetch({"directory": "/nonexistent/path/xyz"})


def test_random_image_source_raises_for_missing_config() -> None:
    plugin = RandomImageSourcePlugin()
    with pytest.raises(ValueError, match="requires 'directory'"):
        plugin.fetch({})


def test_random_image_source_ignores_non_image_files(tmp_path: Path) -> None:
    (tmp_path / "readme.txt").write_text("hello")
    plugin = RandomImageSourcePlugin()
    result = plugin.fetch({"directory": str(tmp_path)})
    assert result.image is None


# ---------------------------------------------------------------------------
# ImagePlacementRenderer
# ---------------------------------------------------------------------------

def _make_panel(x: int = 10, y: int = 20, width: int = 60, height: int = 40) -> PanelDefinition:
    return PanelDefinition(
        source="random_image",
        renderer="random_image",
        slot="image_pool",
        source_config={},
        renderer_config={"x": x, "y": y, "width": width, "height": height},
    )


def test_image_placement_renderer_returns_empty_for_none_image() -> None:
    renderer = ImagePlacementRenderer()
    panel = _make_panel()
    result = renderer.render(RandomImageData(image=None), panel)
    assert result == ()


def test_image_placement_renderer_returns_placement_with_correct_size() -> None:
    renderer = ImagePlacementRenderer()
    panel = _make_panel(x=10, y=20, width=60, height=40)
    img = Image.new("RGB", (200, 150), color=(255, 0, 0))
    result = renderer.render(RandomImageData(image=img), panel)

    assert len(result) == 1
    placement = result[0]
    assert isinstance(placement, ImagePlacement)
    assert placement.x == 10
    assert placement.y == 20
    assert placement.image.size == (60, 40)
    assert placement.image.mode == "L"


def test_image_placement_renderer_uses_defaults_when_config_missing() -> None:
    renderer = ImagePlacementRenderer()
    panel = PanelDefinition(
        source="random_image",
        renderer="random_image",
        slot="image_pool",
        source_config={},
        renderer_config={},
    )
    img = Image.new("RGB", (50, 50))
    result = renderer.render(RandomImageData(image=img), panel)
    assert len(result) == 1
    assert result[0].x == 0
    assert result[0].y == 0
    assert result[0].image.size == (300, 200)


# ---------------------------------------------------------------------------
# _resize_to_fit helper
# ---------------------------------------------------------------------------

def test_resize_to_fit_produces_exact_box_size() -> None:
    img = Image.new("L", (500, 300))
    result = _resize_to_fit(img, 120, 80)
    assert result.size == (120, 80)
    assert result.mode == "L"


def test_resize_to_fit_preserves_aspect_ratio_landscape() -> None:
    """A wide image (2:1) in a square box should have letter-box bars top and bottom."""
    img = Image.new("L", (200, 100), color=0)  # solid black, 2:1
    result = _resize_to_fit(img, 100, 100)
    # The image is white canvas; the resized img is 100x50 centred vertically
    # so top 25 rows and bottom 25 rows should be white (255)
    px = result.load()
    assert px[0, 0] == 255    # top-left corner is background (white)
    assert px[0, 99] == 255   # bottom-left corner is background (white)
