from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from PIL import Image


DashboardData = Any


@dataclass(frozen=True)
class CalendarDate:
    day_of_week: str
    day: int
    month: str


@dataclass(frozen=True)
class WeatherForecast:
    location_name: str
    temperature_min_c: float
    temperature_max_c: float
    precipitation_probability_percent: int
    condition: str


@dataclass(frozen=True)
class DashboardTextBlock:
    slot: str
    lines: tuple[str, ...]
    attributes: dict[str, str] = field(default_factory=dict)


@dataclass
class RandomImageData:
    """Data returned by the random-image source plugin. image is None when the pool is empty."""

    image: Image.Image | None


@dataclass
class ImagePlacement:
    """A PIL image to be composited onto the dashboard at a given position."""

    image: Image.Image
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class PanelDefinition:
    source: str
    renderer: str
    slot: str
    source_config: dict[str, Any]
    renderer_config: dict[str, Any]


@dataclass(frozen=True)
class LayoutConfig:
    template: str
    width: int
    height: int
    preview_output: str | None = None


@dataclass(frozen=True)
class MqttConfig:
    host: str
    port: int
    topic: str
    client_id: str = "epaper-dashboard-service"
    username: str | None = None
    password: str | None = None
    qos: int = 1
    retain: bool = True


@dataclass(frozen=True)
class ServiceConfig:
    """Runtime-loop settings for the cyclic dashboard service."""

    interval_seconds: int = 300


@dataclass(frozen=True)
class DashboardConfiguration:
    layout: LayoutConfig
    mqtt: MqttConfig
    panels: tuple[PanelDefinition, ...]
    service: ServiceConfig = field(default_factory=ServiceConfig)
