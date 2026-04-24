from __future__ import annotations

from epaper_dashboard_service.adapters.layout.svg import SvgLayoutRenderer
from epaper_dashboard_service.adapters.publishing.mqtt import MqttDashboardPublisher
from epaper_dashboard_service.adapters.rendering.image import ImagePlacementRenderer
from epaper_dashboard_service.adapters.rendering.text import CalendarTextRenderer, WeatherTextRenderer
from epaper_dashboard_service.adapters.rendering.train import TrainDepartureTextRenderer
from epaper_dashboard_service.adapters.sources.calendar import CalendarSourcePlugin
from epaper_dashboard_service.adapters.sources.mvg import MvgDepartureSourcePlugin
from epaper_dashboard_service.adapters.sources.random_image import RandomImageSourcePlugin
from epaper_dashboard_service.adapters.sources.weather import OpenMeteoWeatherSourcePlugin
from epaper_dashboard_service.application.service import DashboardApplicationService, PluginRegistry
from epaper_dashboard_service.domain.models import MqttConfig


def build_application(mqtt_config: MqttConfig) -> DashboardApplicationService:
    registry = PluginRegistry(
        sources=(
            CalendarSourcePlugin(),
            OpenMeteoWeatherSourcePlugin(),
            MvgDepartureSourcePlugin(),
            RandomImageSourcePlugin(),
        ),
        renderers=(
            CalendarTextRenderer(),
            WeatherTextRenderer(),
            TrainDepartureTextRenderer(),
            ImagePlacementRenderer(),
        ),
    )
    return DashboardApplicationService(
        registry=registry,
        layout_renderer=SvgLayoutRenderer(),
        publisher=MqttDashboardPublisher(mqtt_config),
    )
