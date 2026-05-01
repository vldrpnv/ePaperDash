# Desktop dashboard service

Python service that builds dashboard images from pluggable data sources, renders them into an SVG layout, converts the result into the 1-bit payload expected by the firmware, and publishes it over MQTT.

Architecture notes, ADRs, and the current specification live in `architecture/`.

## Highlights

- Python 3.12 service with domain-driven and hexagonal structure
- SVG layout templates
- Plugin-based source and renderer registries
- Initial source plugins:
  - calendar
  - weather forecast (Open-Meteo, MET Norway, OpenWeather)
  - MVG departures
  - Fürstenfeldbruck/Eichenau waste collection (AWIDO customer `ffb`)
- Initial renderer plugins:
  - calendar_text
  - weather_text (icon-based timeline with configurable precision)
  - train_departures_text
  - waste_collection_text
- MQTT publisher compatible with the firmware topic payload

## Quick start

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .[dev]
epaper-dashboard-service --config examples/dashboard_config.toml
```

Using `uv` works as well:

```bash
uv venv
. .venv/bin/activate
uv pip install -e '.[dev]'
uv run epaper-dashboard-service --config examples/dashboard_config.toml
```

## Configuration

The service uses TOML. See `examples/dashboard_config.toml`.

- `layout.template`: SVG file path
- `layout.preview_output`: optional PNG preview path
- `layout.width` / `layout.height`: output size
- `mqtt.*`: MQTT publish settings, including `publish_retry_attempts` and `publish_retry_delay_seconds` for broker fault tolerance
- `[[panels]]`: one panel per source plugin

Each panel selects:

- `source`: source plugin name
- `renderer`: renderer plugin name
- `slot`: SVG text element id to populate
- `source_config`: source plugin configuration
- `renderer_config`: renderer plugin configuration

### Weather source configuration

`source = "weather_forecast"` supports multiple free providers under one plugin:

- `provider = "open_meteo"` (default): free hourly forecast, up to 7 days
- `provider = "met_no"`: free hourly forecast (MET Norway API)
- `provider = "openweather"`: free 3-hour forecast blocks (requires `api_key`)

Common `source_config` keys:

- `latitude`, `longitude` (required)
- `location_name` (optional label)
- `forecast_days` (optional, default `5`, max `7`)
- `precision_hours` (optional coarsening at source level, must be a multiple of provider precision)

Provider-specific keys:

- Open-Meteo: optional `timezone`, optional `base_url`
- MET Norway: optional `user_agent`, optional `base_url`
- OpenWeather: required `api_key`, optional `base_url`

### Weather renderer configuration

`renderer = "weather_text"` renders icon-led forecast lines instead of condition words:

- `precision_hours`: coarsen periods for display (for example `4` or `6`)
- `days`: horizon to display (for example `3` to `7`)
- `max_periods`: maximum rendered forecast lines
- `show_provider`: append provider name to the location header

### Fürstenfeldbruck waste collection source configuration

`source = "ffb_waste_collection"` resolves an AWIDO address in customer `ffb` and returns upcoming waste collection events:

- `address` (recommended) — free-form address such as `"Ringstr. 12"`
- or `street` plus optional `house_number`
- `city` (optional, default `Eichenau`)
- `timezone` (optional, default `Europe/Berlin`)
- `waste_type` or `waste_types` (optional) — filter to one or more fractions such as `bio`, `restmuell`, `papier`, or `wertstoff`

### Waste collection renderer configuration

`renderer = "waste_collection_text"` renders waste pickups due within a three-day window starting today:

- each line includes the waste type
- tomorrow's line is bold and larger than the surrounding lines
- `days` (optional, default `3`) adjusts the look-ahead window
- `tomorrow-font-size` (optional) overrides the emphasized font size for tomorrow

## Layouts

The layout template is standard SVG. Two types of slots are supported:

- **Text slots** (`<text id="...">`) — populated by text-based renderers (e.g. `calendar_text`, `weather_text`, `train_departures_text`).  Inline formatting (bold, strikethrough) is emitted as `<tspan>` children per `TextSpan`.  To auto-fit text to a bounding box, add `data-bbox-width` and `data-bbox-height` attributes to the `<text>` element; the renderer calculates an appropriate `font-size` automatically.  Per-renderer text attributes such as `font-size`, `font-family`, `font-weight`, `fill`, and `text-anchor` can be overridden via `renderer_config`.
- **Image slots** (`<image id="...">`) — populated by image-based renderers (e.g. `random_image`, `weather_block`) that return an `ImagePlacement`.  The renderer composites a PIL image into the position declared by the SVG `<image>` element's `x`, `y`, `width`, and `height` attributes.  The `<image>` placeholder is stripped from the SVG before rasterisation so it does not appear in the final bitmap.

Static SVG content such as shapes, dividers, and decorative elements can remain in the template unchanged.
