from __future__ import annotations

import pytest

from epaper_dashboard_service.adapters.sources.weather import OpenMeteoWeatherSourcePlugin
from epaper_dashboard_service.domain.errors import SourceUnavailableError


def test_weather_source_maps_open_meteo_hourly_response() -> None:
    def fake_fetcher(url: str, headers=None):
        assert "latitude=52.52" in url
        return {
            "hourly": {
                "time": [
                    "2026-04-27T00:00",
                    "2026-04-27T01:00",
                    "2026-04-27T02:00",
                    "2026-04-27T03:00",
                ],
                "temperature_2m": [7.0, 8.0, 9.0, 10.0],
                "precipitation_probability": [10, 20, 40, 30],
                "precipitation": [0.0, 0.0, 1.2, 0.4],
                "weather_code": [1, 2, 3, 61],
            }
        }

    plugin = OpenMeteoWeatherSourcePlugin(fetcher=fake_fetcher)
    forecast = plugin.fetch(
        {
            "provider": "open_meteo",
            "location_name": "Eichenau",
            "latitude": 52.52,
            "longitude": 13.41,
            "timezone": "Europe/Berlin",
            "precision_hours": 2,
        }
    )

    assert forecast.location_name == "Eichenau"
    assert forecast.provider == "open_meteo"
    assert forecast.source_precision_hours == 2
    assert len(forecast.periods) == 2
    assert forecast.periods[0].condition_icon == "\u26c5"
    assert forecast.periods[1].condition_icon == "\u2614"
    # coarsened 4 periods into 2: precipitation_mm should be summed per pair
    assert forecast.periods[0].precipitation_mm == pytest.approx(0.0)  # 0.0 + 0.0
    assert forecast.periods[1].precipitation_mm == pytest.approx(1.6)  # 1.2 + 0.4


def test_weather_source_maps_met_no_response() -> None:
    def fake_fetcher(url: str, headers=None):
        assert "api.met.no" in url
        assert headers and "User-Agent" in headers
        return {
            "properties": {
                "timeseries": [
                    {
                        "time": "2026-04-27T00:00:00Z",
                        "data": {
                            "instant": {"details": {"air_temperature": 8.0}},
                            "next_1_hours": {
                                "summary": {"symbol_code": "partlycloudy_day"},
                                "details": {"probability_of_precipitation": 25.0, "precipitation_amount": 0.0},
                            },
                        },
                    },
                    {
                        "time": "2026-04-27T01:00:00Z",
                        "data": {
                            "instant": {"details": {"air_temperature": 9.0}},
                            "next_1_hours": {
                                "summary": {"symbol_code": "lightrain"},
                                "details": {"probability_of_precipitation": 60.0, "precipitation_amount": 1.5},
                            },
                        },
                    },
                ]
            }
        }

    plugin = OpenMeteoWeatherSourcePlugin(fetcher=fake_fetcher)
    forecast = plugin.fetch(
        {
            "provider": "met_no",
            "location_name": "Eichenau",
            "latitude": 48.167,
            "longitude": 11.317,
        }
    )

    assert forecast.provider == "met_no"
    assert forecast.source_precision_hours == 1
    assert len(forecast.periods) == 2
    assert forecast.periods[0].condition_icon == "\u26c5"
    assert forecast.periods[1].condition_icon == "\u2614"
    assert forecast.periods[0].precipitation_mm == pytest.approx(0.0)
    assert forecast.periods[1].precipitation_mm == pytest.approx(1.5)


def test_weather_source_maps_openweather_response() -> None:
    def fake_fetcher(url: str, headers=None):
        assert "api.openweathermap.org" in url
        assert "appid=test-key" in url
        return {
            "list": [
                {
                    "dt_txt": "2026-04-27 00:00:00",
                    "main": {"temp": 8.5},
                    "pop": 0.2,
                    "weather": [{"id": 801}],
                },
                {
                    "dt_txt": "2026-04-27 03:00:00",
                    "main": {"temp": 7.0},
                    "pop": 0.7,
                    "weather": [{"id": 502}],
                    "rain": {"3h": 2.3},
                },
            ]
        }

    plugin = OpenMeteoWeatherSourcePlugin(fetcher=fake_fetcher)
    forecast = plugin.fetch(
        {
            "provider": "openweather",
            "location_name": "Eichenau",
            "latitude": 48.167,
            "longitude": 11.317,
            "api_key": "test-key",
        }
    )

    assert forecast.provider == "openweather"
    assert forecast.source_precision_hours == 3
    assert len(forecast.periods) == 2
    assert forecast.periods[0].condition_icon == "\u26c5"
    assert forecast.periods[1].condition_icon == "\u2614"
    assert forecast.periods[0].precipitation_mm == pytest.approx(0.0)
    assert forecast.periods[1].precipitation_mm == pytest.approx(2.3)


def test_weather_source_validates_required_coordinates() -> None:
    plugin = OpenMeteoWeatherSourcePlugin(fetcher=lambda url: {})

    with pytest.raises(
        ValueError,
        match=r"weather_forecast source requires config value\(s\): latitude, longitude",
    ):
        plugin.fetch({})


def test_weather_source_rejects_unknown_provider() -> None:
    plugin = OpenMeteoWeatherSourcePlugin(fetcher=lambda url, headers=None: {})

    with pytest.raises(ValueError, match="unsupported provider"):
        plugin.fetch({"latitude": 48.167, "longitude": 11.317, "provider": "nope"})


def test_weather_source_maps_timeout_to_source_unavailable() -> None:
    plugin = OpenMeteoWeatherSourcePlugin(
        fetcher=lambda url, headers=None: (_ for _ in ()).throw(TimeoutError("timed out"))
    )

    with pytest.raises(SourceUnavailableError, match="weather_forecast source unavailable"):
        plugin.fetch({"latitude": 52.52, "longitude": 13.41})
