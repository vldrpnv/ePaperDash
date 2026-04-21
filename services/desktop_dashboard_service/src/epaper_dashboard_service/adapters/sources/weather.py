from __future__ import annotations

import json
from typing import Protocol
from urllib.parse import urlencode
from urllib.request import urlopen

from epaper_dashboard_service.domain.models import WeatherForecast
from epaper_dashboard_service.domain.ports import SourcePlugin


class WeatherFetcher(Protocol):
    def __call__(self, url: str) -> dict[str, object]: ...


class OpenMeteoWeatherSourcePlugin(SourcePlugin):
    name = "weather_forecast"

    def __init__(self, fetcher: WeatherFetcher | None = None) -> None:
        self._fetcher = fetcher or _fetch_json

    def fetch(self, config: dict[str, object]) -> WeatherForecast:
        location_name = str(config.get("location_name", "Unknown location"))
        query = urlencode(
            {
                "latitude": config["latitude"],
                "longitude": config["longitude"],
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
                "forecast_days": 1,
                "temperature_unit": "celsius",
                "timezone": config.get("timezone", "UTC"),
            }
        )
        base_url = str(config.get("base_url", "https://api.open-meteo.com/v1/forecast"))
        payload = self._fetcher(f"{base_url}?{query}")
        daily = payload["daily"]
        return WeatherForecast(
            location_name=location_name,
            temperature_min_c=float(daily["temperature_2m_min"][0]),
            temperature_max_c=float(daily["temperature_2m_max"][0]),
            precipitation_probability_percent=int(daily["precipitation_probability_max"][0]),
            condition=_map_weather_code(int(daily["weather_code"][0])),
        )


def _fetch_json(url: str) -> dict[str, object]:
    with urlopen(url, timeout=10) as response:
        return json.load(response)


def _map_weather_code(code: int) -> str:
    mapping = {
        0: "Sunny",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Cloudy",
        45: "Foggy",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Drizzle",
        55: "Dense drizzle",
        61: "Rainy",
        63: "Rainy",
        65: "Heavy rain",
        71: "Light snow",
        73: "Snowy",
        75: "Heavy snow",
        80: "Rain showers",
        81: "Rain showers",
        82: "Heavy showers",
        95: "Thunderstorm",
    }
    return mapping.get(code, "Unknown")
