from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Protocol
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from epaper_dashboard_service.domain.errors import SourceUnavailableError
from epaper_dashboard_service.domain.models import WeatherForecast, WeatherPeriod
from epaper_dashboard_service.domain.ports import SourcePlugin


class WeatherFetcher(Protocol):
    def __call__(self, url: str, headers: dict[str, str] | None = None) -> dict[str, object]: ...


class WeatherForecastSourcePlugin(SourcePlugin):
    name = "weather_forecast"

    def __init__(self, fetcher: WeatherFetcher | None = None) -> None:
        self._fetcher = fetcher or _fetch_json

    def fetch(self, config: dict[str, object]) -> WeatherForecast:
        missing_keys = [key for key in ("latitude", "longitude") if key not in config]
        if missing_keys:
            missing_keys_text = ", ".join(missing_keys)
            raise ValueError(
                f"{self.name} source requires config value(s): {missing_keys_text}"
            )

        location_name = str(config.get("location_name", "Unknown location"))
        latitude = float(config["latitude"])
        longitude = float(config["longitude"])
        forecast_days = max(1, min(int(config.get("forecast_days", 5)), 7))
        provider = str(config.get("provider", "open_meteo")).strip().lower()

        # Config validation that does not require a network call — fail fast.
        if provider not in ("open_meteo", "met_no", "openweather"):
            raise ValueError(f"{self.name} source has unsupported provider: {provider}")

        try:
            periods: tuple[WeatherPeriod, ...]
            source_precision_hours: int
            if provider == "open_meteo":
                payload = self._fetch_open_meteo(config, latitude, longitude, forecast_days)
                periods, source_precision_hours = _parse_open_meteo(payload)
            elif provider == "met_no":
                payload = self._fetch_met_no(config, latitude, longitude)
                periods, source_precision_hours = _parse_met_no(payload, forecast_days)
            else:  # openweather
                payload = self._fetch_openweather(config, latitude, longitude)
                periods, source_precision_hours = _parse_openweather(payload, forecast_days)
        except SourceUnavailableError:
            raise
        except (TimeoutError, URLError, OSError) as error:
            raise SourceUnavailableError(f"{self.name} source unavailable") from error
        except (KeyError, TypeError, ValueError, IndexError) as error:
            raise SourceUnavailableError(f"{self.name} source unavailable: invalid response") from error

        # Precision coarsening — depends on source_precision_hours from the fetch above.
        # These are config validation errors (operator misconfiguration) so they raise ValueError.
        target_precision_hours = int(config.get("precision_hours", source_precision_hours))
        if target_precision_hours < source_precision_hours:
            raise ValueError(
                f"{self.name} source precision_hours ({target_precision_hours}) cannot be finer than "
                f"provider precision ({source_precision_hours})"
            )

        if target_precision_hours % source_precision_hours != 0:
            raise ValueError(
                f"{self.name} source precision_hours ({target_precision_hours}) must be a multiple of "
                f"provider precision ({source_precision_hours})"
            )

        if target_precision_hours != source_precision_hours:
            periods = _coarsen_periods(
                periods,
                source_precision_hours=source_precision_hours,
                target_precision_hours=target_precision_hours,
            )

        return WeatherForecast(
            location_name=location_name,
            provider=provider,
            source_precision_hours=target_precision_hours,
            periods=periods,
        )

    def _fetch_open_meteo(
        self,
        config: dict[str, object],
        latitude: float,
        longitude: float,
        forecast_days: int,
    ) -> dict[str, object]:
        query = urlencode(
            {
                "latitude": latitude,
                "longitude": longitude,
                "hourly": "temperature_2m,precipitation_probability,precipitation,weather_code",
                "forecast_days": forecast_days,
                "temperature_unit": "celsius",
                "timezone": config.get("timezone", "UTC"),
            }
        )
        base_url = str(config.get("base_url", "https://api.open-meteo.com/v1/forecast"))
        return self._fetcher(f"{base_url}?{query}")

    def _fetch_met_no(self, config: dict[str, object], latitude: float, longitude: float) -> dict[str, object]:
        query = urlencode({"lat": latitude, "lon": longitude})
        base_url = str(
            config.get("base_url", "https://api.met.no/weatherapi/locationforecast/2.0/compact")
        )
        user_agent = str(config.get("user_agent", "ePaperDash/1.0 https://github.com"))
        return self._fetcher(f"{base_url}?{query}", headers={"User-Agent": user_agent})

    def _fetch_openweather(
        self,
        config: dict[str, object],
        latitude: float,
        longitude: float,
    ) -> dict[str, object]:
        api_key = config.get("api_key")
        if not api_key:
            raise ValueError("weather_forecast source provider openweather requires config value: api_key")
        query = urlencode(
            {
                "lat": latitude,
                "lon": longitude,
                "appid": api_key,
                "units": "metric",
            }
        )
        base_url = str(config.get("base_url", "https://api.openweathermap.org/data/2.5/forecast"))
        return self._fetcher(f"{base_url}?{query}")


def _fetch_json(url: str, headers: dict[str, str] | None = None) -> dict[str, object]:
    try:
        request = Request(url, headers=headers or {})
        with urlopen(request, timeout=10) as response:
            return json.load(response)
    except (TimeoutError, URLError, OSError, json.JSONDecodeError) as error:
        raise SourceUnavailableError("weather_forecast source unavailable") from error


def _parse_open_meteo(payload: dict[str, object]) -> tuple[tuple[WeatherPeriod, ...], int]:
    hourly = payload["hourly"]
    times = hourly["time"]
    temperatures = hourly["temperature_2m"]
    precip_prob = hourly["precipitation_probability"]
    precip_mm_list = hourly.get("precipitation", [])
    weather_codes = hourly["weather_code"]
    periods: list[WeatherPeriod] = []
    for i, (time_text, temp, pop, code) in enumerate(zip(times, temperatures, precip_prob, weather_codes)):
        start = _parse_datetime(str(time_text))
        label, icon = _map_open_meteo_condition(int(code))
        mm = float(precip_mm_list[i]) if i < len(precip_mm_list) else 0.0
        periods.append(
            WeatherPeriod(
                start_time=start,
                end_time=start + timedelta(hours=1),
                temperature_c=float(temp),
                precipitation_probability_percent=int(pop),
                condition_label=label,
                condition_icon=icon,
                precipitation_mm=mm,
            )
        )
    return tuple(periods), 1


def _parse_met_no(payload: dict[str, object], forecast_days: int) -> tuple[tuple[WeatherPeriod, ...], int]:
    timeseries = payload["properties"]["timeseries"]
    max_entries = forecast_days * 24
    periods: list[WeatherPeriod] = []
    for point in timeseries[:max_entries]:
        start = _parse_datetime(str(point["time"]))
        data = point["data"]
        instant_details = data["instant"]["details"]
        next_one_hour = data.get("next_1_hours") or {}
        summary = next_one_hour.get("summary") or {}
        details = next_one_hour.get("details") or {}

        symbol_code = str(summary.get("symbol_code", "cloudy"))
        label, icon = _map_met_no_symbol(symbol_code)
        precipitation_amount = float(details.get("precipitation_amount", 0.0))
        precipitation_probability = details.get("probability_of_precipitation")
        if precipitation_probability is None:
            precipitation_probability = min(100, int(round(precipitation_amount * 50)))

        periods.append(
            WeatherPeriod(
                start_time=start,
                end_time=start + timedelta(hours=1),
                temperature_c=float(instant_details["air_temperature"]),
                precipitation_probability_percent=int(precipitation_probability),
                condition_label=label,
                condition_icon=icon,
                precipitation_mm=precipitation_amount,
            )
        )
    return tuple(periods), 1


def _parse_openweather(payload: dict[str, object], forecast_days: int) -> tuple[tuple[WeatherPeriod, ...], int]:
    entries = payload["list"]
    max_entries = forecast_days * 8
    periods: list[WeatherPeriod] = []
    for entry in entries[:max_entries]:
        start = _parse_datetime(str(entry["dt_txt"]))
        weather_id = int(entry["weather"][0]["id"])
        label, icon = _map_openweather_condition(weather_id)
        rain_mm = float((entry.get("rain") or {}).get("3h", 0.0))
        snow_mm = float((entry.get("snow") or {}).get("3h", 0.0))
        periods.append(
            WeatherPeriod(
                start_time=start,
                end_time=start + timedelta(hours=3),
                temperature_c=float(entry["main"]["temp"]),
                precipitation_probability_percent=int(round(float(entry.get("pop", 0.0)) * 100)),
                condition_label=label,
                condition_icon=icon,
                precipitation_mm=rain_mm + snow_mm,
            )
        )
    return tuple(periods), 3


def _coarsen_periods(
    periods: tuple[WeatherPeriod, ...],
    source_precision_hours: int,
    target_precision_hours: int,
) -> tuple[WeatherPeriod, ...]:
    group_size = target_precision_hours // source_precision_hours
    grouped: list[WeatherPeriod] = []
    for start_index in range(0, len(periods), group_size):
        chunk = periods[start_index : start_index + group_size]
        if not chunk:
            continue
        avg_temp = sum(period.temperature_c for period in chunk) / len(chunk)
        max_pop = max(period.precipitation_probability_percent for period in chunk)
        representative = max(
            chunk,
            key=lambda period: (_icon_severity(period.condition_icon), period.precipitation_probability_percent),
        )
        total_mm = sum(period.precipitation_mm for period in chunk)
        grouped.append(
            WeatherPeriod(
                start_time=chunk[0].start_time,
                end_time=chunk[-1].end_time,
                temperature_c=avg_temp,
                precipitation_probability_percent=max_pop,
                condition_label=representative.condition_label,
                condition_icon=representative.condition_icon,
                precipitation_mm=total_mm,
            )
        )
    return tuple(grouped)


def _parse_datetime(value: str) -> datetime:
    if value.endswith("Z"):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    elif "T" in value:
        parsed = datetime.fromisoformat(value)
    else:
        parsed = datetime.fromisoformat(value.replace(" ", "T"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _map_open_meteo_condition(code: int) -> tuple[str, str]:
    mapping: dict[int, tuple[str, str]] = {
        0: ("Sunny", "\u2600"),
        1: ("Mainly clear", "\u2600"),
        2: ("Partly cloudy", "\u26c5"),
        3: ("Cloudy", "\u2601"),
        45: ("Foggy", "\U0001f32b"),
        48: ("Foggy", "\U0001f32b"),
        51: ("Light drizzle", "\u2614"),
        53: ("Drizzle", "\u2614"),
        55: ("Dense drizzle", "\u2614"),
        61: ("Rainy", "\u2614"),
        63: ("Rainy", "\u2614"),
        65: ("Heavy rain", "\u2614"),
        71: ("Light snow", "\u2744"),
        73: ("Snow", "\u2744"),
        75: ("Heavy snow", "\u2744"),
        80: ("Rain showers", "\u2614"),
        81: ("Rain showers", "\u2614"),
        82: ("Heavy showers", "\u2614"),
        95: ("Thunderstorm", "\u26a1"),
    }
    return mapping.get(code, ("Unknown", "\u2753"))


def _map_met_no_symbol(symbol_code: str) -> tuple[str, str]:
    code = symbol_code.lower()
    if "thunder" in code:
        return "Thunderstorm", "\u26a1"
    if "snow" in code or "sleet" in code:
        return "Snow", "\u2744"
    if "rain" in code or "drizzle" in code:
        return "Rain", "\u2614"
    if "fog" in code:
        return "Fog", "\U0001f32b"
    if "partlycloudy" in code:
        return "Partly cloudy", "\u26c5"
    if "clearsky" in code or "fair" in code:
        return "Sunny", "\u2600"
    if "cloudy" in code:
        return "Cloudy", "\u2601"
    return "Unknown", "\u2753"


def _map_openweather_condition(weather_id: int) -> tuple[str, str]:
    if 200 <= weather_id < 300:
        return "Thunderstorm", "\u26a1"
    if 300 <= weather_id < 400:
        return "Drizzle", "\u2614"
    if 500 <= weather_id < 600:
        return "Rain", "\u2614"
    if 600 <= weather_id < 700:
        return "Snow", "\u2744"
    if weather_id == 800:
        return "Sunny", "\u2600"
    if 801 <= weather_id < 900:
        return "Cloudy", "\u26c5"
    return "Unknown", "\u2753"


def _icon_severity(icon: str) -> int:
    severity = {
        "\u26a1": 5,
        "\u2614": 4,
        "\u2744": 4,
        "\U0001f32b": 3,
        "\u2601": 2,
        "\u26c5": 1,
        "\u2600": 0,
        "\u2753": -1,
    }
    return severity.get(icon, -1)


# Backward compatible alias for previous class name.
OpenMeteoWeatherSourcePlugin = WeatherForecastSourcePlugin
