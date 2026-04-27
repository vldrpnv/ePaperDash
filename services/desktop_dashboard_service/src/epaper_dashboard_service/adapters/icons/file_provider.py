"""File-based weather icon provider.

Loads SVG icon files from a directory and rasterizes them via cairosvg.
Each icon is cached by (condition_icon, width, height) to avoid repeated disk I/O.

The mapping from condition_icon string to filename is defined in ICON_MAP.
To change the icon set, point a new ``FileWeatherIconProvider`` at a different
directory whose files match the names in ICON_MAP (or subclass and override
``_filename_for``).
"""
from __future__ import annotations

from functools import lru_cache
from io import BytesIO
from pathlib import Path

import cairosvg
from PIL import Image

from epaper_dashboard_service.domain.ports import WeatherIconProvider

# Maps the condition_icon Unicode character to a filename inside the icons directory.
# Add entries here when new condition icons are introduced in the weather source.
ICON_MAP: dict[str, str] = {
    "\u2600": "sunny.svg",           # ☀ Sunny / Mainly clear
    "\u26c5": "partly_cloudy.svg",   # ⛅ Partly cloudy
    "\u2601": "overcast.svg",        # ☁ Cloudy / Overcast
    "\u2614": "rain.svg",            # ☔ Rain / Drizzle / Showers
    "\u2744": "snow.svg",            # ❄ Snow / Sleet
    "\u26a1": "thunderstorm.svg",    # ⚡ Thunderstorm
    "\U0001f32b": "fog.svg",         # 🌫 Fog
}


class FileWeatherIconProvider(WeatherIconProvider):
    """Load weather icons from SVG files in *icons_dir*.

    The directory must contain SVG files whose names match the values in
    :data:`ICON_MAP`.  Missing files are silently skipped; callers receive
    ``None`` and should fall back to text rendering.

    Args:
        icons_dir: Directory containing the icon SVG files.
    """

    def __init__(self, icons_dir: Path) -> None:
        self._icons_dir = icons_dir

    def get_icon(self, condition_icon: str, width: int, height: int) -> Image.Image | None:
        filename = self._filename_for(condition_icon)
        if filename is None:
            return None
        return _load_icon(self._icons_dir, filename, width, height)

    def _filename_for(self, condition_icon: str) -> str | None:
        """Return the filename for *condition_icon*, or ``None`` if unmapped."""
        return ICON_MAP.get(condition_icon)


@lru_cache(maxsize=64)
def _load_icon(icons_dir: Path, filename: str, width: int, height: int) -> Image.Image | None:
    icon_path = icons_dir / filename
    if not icon_path.exists():
        return None
    try:
        png_bytes = cairosvg.svg2png(
            url=str(icon_path),
            output_width=width,
            output_height=height,
        )
        # Load as RGBA so we can access the alpha channel.
        # Transparent areas have premultiplied RGB=(0,0,0) which becomes black
        # after a naive convert("L"), making the icon appear inverted (dark
        # background, light shapes).  Instead, derive the icon mask directly
        # from the alpha: opaque drawn pixels → black (0), transparent → white (255).
        img_rgba = Image.open(BytesIO(png_bytes)).convert("RGBA")
        *_, alpha = img_rgba.split()
        return alpha.point(lambda v: 0 if v > 64 else 255)
    except Exception:  # noqa: BLE001 — don't crash the dashboard on a missing/corrupt icon
        return None
