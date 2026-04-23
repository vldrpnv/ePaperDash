from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


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
class TextSpan:
    """A fragment of a line with optional inline formatting."""

    text: str
    bold: bool = False
    strikethrough: bool = False


# A rich line is a sequence of TextSpan fragments; a plain line is a str.
RichLine = tuple[TextSpan, ...]


@dataclass(frozen=True)
class DashboardTextBlock:
    slot: str
    lines: tuple[str | RichLine, ...]
    attributes: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class TrainDeparture:
    line: str
    destination: str
    scheduled_time: datetime
    actual_time: datetime | None
    cancelled: bool


@dataclass(frozen=True)
class TrainDepartures:
    station_name: str
    entries: tuple[TrainDeparture, ...]


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
class DashboardConfiguration:
    layout: LayoutConfig
    mqtt: MqttConfig
    panels: tuple[PanelDefinition, ...]
