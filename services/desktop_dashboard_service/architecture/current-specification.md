# Current specification

## Purpose

The desktop dashboard service generates dashboard images for the firmware, using pluggable data sources and renderers, then publishes the result to MQTT.

## Runtime flow

The CLI currently accepts `--config <path>` and performs the following steps:

1. load TOML configuration from disk
2. resolve the layout template path relative to the config file
3. bootstrap the application with the built-in source and renderer plugins
4. for each configured panel:
   - fetch source data through the named source plugin
   - render that data through the named renderer plugin
   - collect one or more `DashboardTextBlock` values
  - when a source is temporarily unavailable, skip only that panel and continue the cycle
5. render all text blocks into the configured SVG template
6. rasterize the SVG into a grayscale image
7. convert the image to a 1-bit payload
8. optionally save a preview image when `layout.preview_output` is configured
9. publish the payload to the configured MQTT topic
  - publish retries transient broker failures with bounded attempts and delay

## Current module responsibilities

- `domain`
  - immutable models for configuration and dashboard data
  - abstract ports for sources, renderers, layout rendering, and publishing
- `application`
  - configuration loading
  - plugin lookup
  - orchestration of the fetch → render → layout → encode → publish pipeline
- `adapters`
  - calendar and weather sources
  - text renderers for calendar and weather output
  - SVG layout renderer
  - MQTT publisher
- `bootstrap`
  - wires the built-in adapters into the application service
- `cli`
  - parses arguments and starts one end-to-end execution

## Configuration contract

A valid configuration currently requires:

- `[layout]`
  - `template`
  - optional `preview_output`
  - optional `width` and `height` with defaults `800` and `480`
- `[mqtt]`
  - `host`
  - `topic`
  - optional `port`, `client_id`, `username`, `password`, `qos`, `retain`, `publish_retry_attempts`, and `publish_retry_delay_seconds`
- `[[panels]]`
  - at least one panel
  - each panel requires `source`, `renderer`, and `slot`
  - each panel may include `source_config` and `renderer_config`

## Extension contract

### Source plugins

A source plugin exposes a unique `name` and returns one domain object from `fetch(config)`.

When a source cannot provide data because of transient availability problems (for example timeout, connection error, or temporary upstream failure), it must raise `SourceUnavailableError`. The application service isolates that failure to the affected panel and continues rendering other panels.

The built-in `weather_forecast` source returns a weather timeline contract with provider metadata:

- `location_name`
- `provider`
- `source_precision_hours`
- `periods[]` where each period contains:
  - `start_time`, `end_time`
  - `temperature_c`
  - `precipitation_probability_percent`
  - `precipitation_mm` (total precipitation in mm for the period; defaults to `0.0`)
  - `condition_label`
  - `condition_icon`

The weather source supports `provider = open_meteo | met_no | openweather` and optional source-level precision coarsening through `source_config.precision_hours`.

### Renderer plugins

A renderer plugin exposes a unique `name`, declares `supported_type`, and returns one or more `DashboardTextBlock` or `ImagePlacement` values from `render(data, panel)`.

The built-in `weather_text` renderer accepts weather timeline data and supports precision-aware display through `renderer_config.precision_hours`, `renderer_config.days`, and `renderer_config.max_periods`.

The built-in `weather_block` renderer accepts weather timeline data and produces a single `ImagePlacement` — a self-contained PIL image composited onto the dashboard.  It renders three rows:
- Row 1: today overview (condition, temperature range, precipitation if notable).
- Row 2: three smart 4-hour blocks covering the remainder of today, carrying over to the next day when fewer than three slots remain.  Each block shows a weather icon, time label, and temperature range.
- Row 3: tomorrow overview (small icon, condition, temperature range, precipitation if notable).

The `weather_block` renderer delegates icon rendering to a `WeatherIconProvider`.  The built-in `FileWeatherIconProvider` loads SVG icon files from `adapters/icons/weather/` and rasterizes them via cairosvg.  The `NullWeatherIconProvider` always returns `None` (useful for testing and fallback).  The provider interface is defined in `domain/ports.py` as `WeatherIconProvider`; custom providers can be registered in `bootstrap.py`.

Font rendering in `weather_block` uses bundled DejaVu Sans TTF files in `adapters/fonts/` and carries no system font dependency.  The font path can be overridden via `renderer_config.font_path`.

The built-in `analog_clock` renderer accepts clock data and produces a single `ImagePlacement` — a self-contained PIL image composited onto the dashboard.  It renders:
- An outer clock circle.
- Optional 12-position tick marks (one per 5-minute position).
- An optional hour hand (no minute hand, no second hand).
- A highlighted outer-arc sector representing the validity window of the rendered dashboard image.
- An optional text label below the clock showing the validity range.

The `analog_clock` renderer accepts the following `renderer_config` keys (all optional):
- `size_px` (int, default 80): diameter of the clock face in pixels.
- `validity_window_minutes` (int, default 5): width of the validity window.
- `window_start_mode` (str, default `"start_at_next_minute"`): `"start_at_render_time"` or `"start_at_next_minute"`.
- `label_mode` (str, default `"range"`): `"none"`, `"range"`, or `"approx"`.
- `sector_style` (str, default `"outer_arc"`): `"outer_arc"` draws a thick arc along the clock rim spanning the full validity window; `"end_hand"` draws a single long hand pointing to the end of the validity window.
- `show_hour_hand` (bool, default true).
- `show_tick_marks` (bool, default true).
- `x` / `y` (int, default 0): placement coordinates, overridden by SVG slot geometry.

Window start modes:
- `start_at_next_minute`: if the render time has any sub-minute component, round up to the next whole minute; otherwise use the exact minute. Example: render at 21:26:49 → window 21:27–21:32.
- `start_at_render_time`: use the exact render timestamp as the window start.

### Layout contract

- Panels target SVG elements by `slot` id.
- The SVG renderer supports `<text>` targets for text blocks and `<image>` targets for image placements.
- When an SVG template declares `<image id="weather_block" ...>`, the application service reads its `x`, `y`, `width`, and `height` attributes and injects them into the renderer's `renderer_config`.  The `weather_block` renderer uses these values to size and position the composited image.
- If the SVG template declares a `<text id="last_update">` slot, the application injects a local-time timestamp line on every successful render cycle.
- Plain lines are strings; rich lines are `tuple[TextSpan, ...]` where each `TextSpan` carries optional `bold` and `strikethrough` flags.  Each span is emitted as a nested `<tspan>` with the corresponding SVG attributes.
- Multi-line content (both plain and rich) is emitted as nested `<tspan>` elements with `dy="1.2em"` for each subsequent line.
- Renderer attributes from `DashboardTextBlock.attributes` are passed through verbatim to the target `<text>` element and overwrite any existing attributes with the same names.
- When a `<text>` element in the SVG template carries both `data-bbox-width` and `data-bbox-height` attributes, the renderer calculates and sets `font-size` automatically so that all lines fit within the declared bounding box.  Any `font-size` set in `renderer_config` takes precedence over the auto-calculated value.

## Built-in plugin inventory

### Sources

- `calendar`
- `clock` — returns a `ClockData` with the current timezone-aware `render_time`; supports `source_config.timezone` (IANA timezone name, default `"UTC"`)
- `weather_forecast` with provider selection:
  - Open-Meteo (free hourly forecast)
  - MET Norway (free hourly forecast)
  - OpenWeather 5-day forecast in 3-hour blocks
- `mvg_departures` backed by the MVG BGW-PT v3 API (no registration required)
  - supports optional `source_config.timezone` (IANA timezone name) for normalizing departure times before rendering
  - defaults to `Europe/Berlin` when `timezone` is not set

### Renderers

- `calendar_text`
- `analog_clock` (self-contained PIL image: outer circle, tick marks, hour hand, outer-arc validity sector, optional range/approx label)
- `weather_text` (icon-based weather timeline, SVG text output)
- `weather_block` (self-contained PIL image: today overview + 4-h blocks + tomorrow row)
- `train_departures_text` — the station name header is a **bold** `RichLine`; each departure is rendered as a single timetable row (one `StyledLine`) containing the line label, departure time(s), and destination on the same line.  The line label is shown in **bold** for the first occurrence; subsequent departures sharing the same line label use space padding to keep the time column aligned.  Delayed departures show the scheduled time as strikethrough followed by the actual time in **bold**.  Cancelled departures show the scheduled time as strikethrough followed by "Cancelled" and the destination.  When `first-departure-font-size` is set in `renderer_config`, the first (next) departure row is rendered at that font size to give it visual emphasis over subsequent rows; if not set, `departure-font-size` applies to all rows.

## Output contract

- The rendered image is converted to Pillow mode `1` before MQTT publishing.
- The published payload must remain compatible with the firmware bitmap contract.
- MQTT publishing retries transient failures with bounded attempts before surfacing an error.

## Reliability and fault handling

- Source unavailability is isolated at panel level; one unavailable source must not abort the full dashboard build.
- For every unavailable panel, the layout slot is cleared so stale placeholder or old content is not rendered.
- MQTT broker outages are retried with bounded attempts and delay per cycle.
- A failed publish cycle does not terminate the long-running CLI loop; the next scheduled cycle retries.
- Non-transient configuration or wiring errors (for example unknown plugin, renderer type mismatch, invalid required source configuration) still fail fast.

## Acceptance criteria

- If a panel source raises `SourceUnavailableError`, the service still renders and encodes the dashboard with remaining panels.
- Slots bound to unavailable sources are rendered as empty text (no visible stale block content).
- Transient weather and MVG source fetch failures are mapped to `SourceUnavailableError`.
- `mvg_departures` normalizes planned and realtime times to `Europe/Berlin` by default.
- If `mvg_departures.source_config.timezone` is set to a valid IANA timezone, planned and realtime times are normalized to that timezone.
- If MQTT publish fails transiently, the publisher retries according to `mqtt.publish_retry_attempts` and `mqtt.publish_retry_delay_seconds`.
- If publish still fails after retries, the CLI logs the cycle failure and continues with the next interval.
- `weather_forecast` can fetch forecasts for Eichenau (or any configured coordinates) from `open_meteo`, `met_no`, or `openweather` through one source plugin contract.
- The weather timeline carries provider precision and supports source-level coarsening when `source_config.precision_hours` is configured.
- `weather_text` renders icon-led forecast lines (without condition words such as "Cloudy") and supports display precision coarsening through `renderer_config.precision_hours`.
- If the layout contains a `<text id="last_update">` element, each generated dashboard includes a `Last update: YYYY-MM-DD HH:MM:SS ±HHMM` line using the host local timezone offset.
- If the layout does not contain `last_update`, dashboard generation continues without errors and without injecting an extra slot.
- `train_departures_text` renders each departure as a single timetable row: line label (bold on first occurrence of each line, space-padded on subsequent same-line rows), scheduled time, destination — all on one line.
- Delayed departure actual times are shown in **bold**; cancelled departure scheduled times are shown as strikethrough.
- When `first-departure-font-size` is set, the first departure row is rendered at that font size for visual emphasis; subsequent rows use `departure-font-size`.
- The layout slot bounding boxes in `layout.svg` must not overlap; the two-zone layout separates the left context rail (x 0–182) from the main content area (x 188–800), with the weather block in the main area top section (height 200 px) and the transport timetable in the lower portion (y ≥ 212).
- `analog_clock` renders an outer circle, optional tick marks, and an optional hour hand, with no minute hand and no second hand.
- `analog_clock` `sector_style = "outer_arc"` (default) renders a highlighted thick arc along the clock rim spanning the validity window.
- `analog_clock` `sector_style = "end_hand"` renders a single long hand pointing to the end of the validity window instead of an arc.
- `analog_clock` `window_start_mode = "start_at_next_minute"` rounds the render time up to the next whole minute when sub-minute components are present.  Example: render at 21:26:49 produces window 21:27–21:32.
- `analog_clock` `window_start_mode = "start_at_render_time"` uses the exact render timestamp as the window start.
- `analog_clock` `label_mode = "range"` renders a `HH:MM–HH:MM` label below the clock face.
- `analog_clock` `label_mode = "approx"` renders a `ca. HH:MM` label below the clock face.
- `analog_clock` `label_mode = "none"` renders no label; image height equals `size_px`.
- `clock` source returns a timezone-aware `ClockData.render_time` using the configured IANA timezone (default `"UTC"`).
