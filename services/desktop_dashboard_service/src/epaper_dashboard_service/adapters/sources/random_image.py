from __future__ import annotations

import random
from pathlib import Path

from PIL import Image

from epaper_dashboard_service.domain.models import RandomImageData
from epaper_dashboard_service.domain.ports import SourcePlugin

_SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tiff", ".tif"}


class RandomImageSourcePlugin(SourcePlugin):
    name = "random_image"

    def fetch(self, config: dict[str, object]) -> RandomImageData:
        directory_str = config.get("directory")
        if not directory_str:
            raise ValueError("random_image source requires 'directory' in source_config")

        directory = Path(str(directory_str))
        if not directory.is_dir():
            raise ValueError(f"random_image source: directory does not exist: {directory}")

        candidates = [
            p for p in directory.iterdir()
            if p.is_file() and p.suffix.lower() in _SUPPORTED_EXTENSIONS
        ]

        if not candidates:
            return RandomImageData(image=None)

        chosen = random.choice(candidates)
        image = Image.open(chosen)
        # Load pixel data immediately so the file handle can be released
        image.load()
        return RandomImageData(image=image)
