from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from PIL import Image

from epaper_dashboard_service.domain.models import DashboardTextBlock, ImagePlacement, PanelDefinition


class SourcePlugin(ABC):
    name: str

    @abstractmethod
    def fetch(self, config: dict[str, Any]) -> Any:
        """Fetch data for a panel.

        Implementations should raise SourceUnavailableError for transient failures
        such as network timeouts or temporary upstream outages.
        """
        raise NotImplementedError


class RendererPlugin(ABC):
    name: str
    supported_type: type[Any]

    @abstractmethod
    def render(self, data: Any, panel: PanelDefinition) -> tuple[DashboardTextBlock | ImagePlacement, ...]:
        raise NotImplementedError


class LayoutRenderer(ABC):
    @abstractmethod
    def render(
        self,
        template_path: Path,
        blocks: tuple[DashboardTextBlock, ...],
        width: int,
        height: int,
        cleared_slots: tuple[str, ...] = (),
        svg_output: Path | None = None,
    ) -> Image.Image:
        raise NotImplementedError


class DashboardPublisher(ABC):
    @abstractmethod
    def publish(self, payload: bytes) -> None:
        raise NotImplementedError


class WeatherIconProvider(ABC):
    """Return a grayscale PIL Image for a given condition icon string at the requested size.

    Returns ``None`` when the provider has no image for the condition (callers must
    fall back to text rendering in that case).
    """

    @abstractmethod
    def get_icon(self, condition_icon: str, width: int, height: int) -> "Image.Image | None":
        raise NotImplementedError
