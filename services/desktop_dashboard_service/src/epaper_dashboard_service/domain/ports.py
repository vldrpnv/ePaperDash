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
        raise NotImplementedError


class RendererPlugin(ABC):
    name: str
    supported_type: type[Any]

    @abstractmethod
    def render(self, data: Any, panel: PanelDefinition) -> tuple[DashboardTextBlock | ImagePlacement, ...]:
        raise NotImplementedError


class LayoutRenderer(ABC):
    @abstractmethod
    def render(self, template_path: Path, blocks: tuple[DashboardTextBlock, ...], width: int, height: int) -> Image.Image:
        raise NotImplementedError


class DashboardPublisher(ABC):
    @abstractmethod
    def publish(self, payload: bytes) -> None:
        raise NotImplementedError
