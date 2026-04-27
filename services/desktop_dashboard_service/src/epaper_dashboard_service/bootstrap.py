from __future__ import annotations

from pathlib import Path

from epaper_dashboard_service.adapters.icons.file_provider import FileWeatherIconProvider
from epaper_dashboard_service.adapters.layout.svg import SvgLayoutRenderer
from epaper_dashboard_service.adapters.publishing.mqtt import MqttDashboardPublisher
from epaper_dashboard_service.adapters.rendering.clock import AnalogClockRenderer
from epaper_dashboard_service.adapters.rendering.image import ImagePlacementRenderer
from epaper_dashboard_service.adapters.rendering.text import CalendarTextRenderer, WeatherTextRenderer
from epaper_dashboard_service.adapters.rendering.train import TrainDepartureTextRenderer
from epaper_dashboard_service.adapters.rendering.weather import WeatherBlockRenderer
from epaper_dashboard_service.adapters.sources.calendar import CalendarSourcePlugin
from epaper_dashboard_service.adapters.sources.clock import ClockSourcePlugin
from epaper_dashboard_service.adapters.sources.mvg import MvgDepartureSourcePlugin
from epaper_dashboard_service.adapters.sources.random_image import RandomImageSourcePlugin
from epaper_dashboard_service.adapters.sources.weather import WeatherForecastSourcePlugin
from epaper_dashboard_service.application.service import DashboardApplicationService, PluginRegistry
from epaper_dashboard_service.domain.models import MqttConfig

_ICONS_DIR = Path(__file__).parent / "adapters" / "icons" / "weather"


def build_application(mqtt_config: MqttConfig) -> DashboardApplicationService:
    icon_provider = FileWeatherIconProvider(_ICONS_DIR)
    registry = PluginRegistry(
        sources=(
            CalendarSourcePlugin(),
            WeatherForecastSourcePlugin(),
            MvgDepartureSourcePlugin(),
            RandomImageSourcePlugin(),
            ClockSourcePlugin(),
        ),
        renderers=(
            CalendarTextRenderer(),
            WeatherTextRenderer(),
            WeatherBlockRenderer(icon_provider=icon_provider),
            TrainDepartureTextRenderer(),
            ImagePlacementRenderer(),
            AnalogClockRenderer(),
        ),
    )
    return DashboardApplicationService(
        registry=registry,
        layout_renderer=SvgLayoutRenderer(),
        publisher=MqttDashboardPublisher(mqtt_config),
    )
