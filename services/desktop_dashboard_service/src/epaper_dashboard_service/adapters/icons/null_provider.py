"""Null weather icon provider — always returns None (graceful fallback)."""
from __future__ import annotations

from PIL import Image

from epaper_dashboard_service.domain.ports import WeatherIconProvider


class NullWeatherIconProvider(WeatherIconProvider):
    """A no-op provider that never returns an image.

    Useful as a fallback and for testing renderers without real icon files.
    """

    def get_icon(self, condition_icon: str, width: int, height: int) -> Image.Image | None:
        return None
