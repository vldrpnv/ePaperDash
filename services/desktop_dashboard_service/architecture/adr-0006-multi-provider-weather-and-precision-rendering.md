# ADR-0006: Use a multi-provider weather timeline contract with precision-aware icon rendering

## Status

Accepted

## Context

The weather panel currently depends on one provider and one-day summary fields. The dashboard now needs:

- alternative free weather providers for resilience
- forecast precision better than one day (for example hourly or 3-4 hour blocks)
- configurable 3-7 day horizons
- icon-led weather rendering instead of condition words like "Cloudy"

## Decision

Use one source plugin (`weather_forecast`) that supports multiple providers selected by `source_config.provider`:

- `open_meteo` (default, free hourly forecast)
- `met_no` (MET Norway, free hourly forecast)
- `openweather` (free tier, 3-hour forecast, API key required)

Unify all providers into one domain model:

- `WeatherForecast(location_name, provider, source_precision_hours, periods)`
- `WeatherPeriod(start_time, end_time, temperature_c, precipitation_probability_percent, condition_label, condition_icon)`

Allow optional source-level coarsening through `source_config.precision_hours` when it is a multiple of provider precision.

Update `weather_text` renderer to render icon-led timeline entries and support renderer-level display coarsening and horizon controls:

- `renderer_config.precision_hours`
- `renderer_config.days`
- `renderer_config.max_periods`
- `renderer_config.show_provider`

## Consequences

- Weather provider outages can be mitigated by switching provider in configuration without changing panel wiring.
- Source and renderer now share an explicit precision-aware contract.
- Weather output becomes denser and more useful for short-term planning while keeping the same text-slot SVG pipeline.
- The MQTT bitmap contract with firmware remains unchanged.
