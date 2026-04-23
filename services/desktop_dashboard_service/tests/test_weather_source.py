from __future__ import annotations

import pytest

from epaper_dashboard_service.adapters.sources.weather import OpenMeteoWeatherSourcePlugin


def test_weather_source_maps_open_meteo_response() -> None:
    def fake_fetcher(url: str):
        assert "latitude=52.52" in url
        return {
            "daily": {
                "temperature_2m_min": [7.2],
                "temperature_2m_max": [15.4],
                "precipitation_probability_max": [35],
                "weather_code": [2],
            }
        }

    plugin = OpenMeteoWeatherSourcePlugin(fetcher=fake_fetcher)
    forecast = plugin.fetch(
        {
            "location_name": "Berlin",
            "latitude": 52.52,
            "longitude": 13.41,
            "timezone": "Europe/Berlin",
        }
    )

    assert forecast.location_name == "Berlin"
    assert forecast.condition == "Partly cloudy"
    assert forecast.temperature_min_c == 7.2
    assert forecast.temperature_max_c == 15.4
    assert forecast.precipitation_probability_percent == 35


def test_weather_source_validates_required_config_keys() -> None:
    plugin = OpenMeteoWeatherSourcePlugin(fetcher=lambda url: {})

    with pytest.raises(
        ValueError,
        match="weather_forecast source requires config value\\(s\\): latitude, longitude",
    ):
        plugin.fetch({})
