from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from PIL import Image


DashboardData = Any


@dataclass(frozen=True)
class CalendarDate:
    day_of_week: str
    day: int
    month: str


@dataclass(frozen=True)
class WeatherPeriod:
    start_time: datetime
    end_time: datetime
    temperature_c: float
    precipitation_probability_percent: int
    condition_label: str
    condition_icon: str
    precipitation_mm: float = 0.0


@dataclass(frozen=True)
class WeatherForecast:
    location_name: str
    provider: str
    source_precision_hours: int
    periods: tuple[WeatherPeriod, ...]


@dataclass(frozen=True)
class TextSpan:
    """A fragment of a line with optional inline formatting."""

    text: str
    bold: bool = False
    strikethrough: bool = False


# A rich line is a sequence of TextSpan fragments; a plain line is a str.
RichLine = tuple[TextSpan, ...]


@dataclass(frozen=True)
class StyledLine:
    """A rich line with optional per-line SVG attribute overrides.

    The ``spans`` field carries the same content as a plain ``RichLine``.
    When ``font_size`` is set the SVG renderer emits a ``font-size`` attribute
    on the outer ``<tspan>`` wrapper, overriding the parent ``<text>`` element
    font size for that line only.
    When ``dy`` is set it replaces the default ``1.2em`` line-advance used by
    the SVG renderer, allowing custom spacing above a specific line.
    """

    spans: RichLine
    font_size: int | None = None
    dy: str | None = None


@dataclass(frozen=True)
class DashboardTextBlock:
    slot: str
    lines: tuple[str | RichLine | StyledLine, ...]
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


@dataclass(frozen=True)
class ClockData:
    """Data for the analog validity-window clock renderer."""

    render_time: datetime


@dataclass(frozen=True)
class GoogleCalendarEvent:
    """A single event fetched from a Google Calendar iCal feed."""

    title: str
    event_date: date
    start_time: datetime | None  # None when the event is all-day
    end_time: datetime | None    # None when the event is all-day
    all_day: bool


@dataclass(frozen=True)
class GoogleCalendarEvents:
    """Three-day Google Calendar events from a Google Calendar iCal feed."""

    reference_date: date
    events: tuple[GoogleCalendarEvent, ...]


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
class WasteCollectionEntry:
    date: date
    waste_type: str


@dataclass(frozen=True)
class WasteCollectionSchedule:
    address_label: str
    reference_date: date
    entries: tuple[WasteCollectionEntry, ...]


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
    publish_retry_attempts: int = 3
    publish_retry_delay_seconds: float = 1.0


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
