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
5. render all text blocks into the configured SVG template
6. rasterize the SVG into a grayscale image
7. convert the image to a 1-bit payload
8. optionally save a preview image when `layout.preview_output` is configured
9. publish the payload to the configured MQTT topic

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
  - optional `port`, `client_id`, `username`, `password`, `qos`, and `retain`
- `[[panels]]`
  - at least one panel
  - each panel requires `source`, `renderer`, and `slot`
  - each panel may include `source_config` and `renderer_config`

## Extension contract

### Source plugins

A source plugin exposes a unique `name` and returns one domain object from `fetch(config)`.

### Renderer plugins

A renderer plugin exposes a unique `name`, declares `supported_type`, and returns one or more `DashboardTextBlock` values from `render(data, panel)`.

### Layout contract

- Panels target SVG elements by `slot` id.
- The current SVG renderer only supports `<text>` targets.
- Plain lines are strings; rich lines are `tuple[TextSpan, ...]` where each `TextSpan` carries optional `bold` and `strikethrough` flags.  Each span is emitted as a nested `<tspan>` with the corresponding SVG attributes.
- Multi-line content (both plain and rich) is emitted as nested `<tspan>` elements with `dy="1.2em"` for each subsequent line.
- Renderer attributes from `DashboardTextBlock.attributes` are passed through verbatim to the target `<text>` element and overwrite any existing attributes with the same names.
- When a `<text>` element in the SVG template carries both `data-bbox-width` and `data-bbox-height` attributes, the renderer calculates and sets `font-size` automatically so that all lines fit within the declared bounding box.  Any `font-size` set in `renderer_config` takes precedence over the auto-calculated value.

## Built-in plugin inventory

### Sources

- `calendar`
- `weather_forecast` backed by Open-Meteo
- `mvg_departures` backed by the MVG FIB v2 API (no registration required)

### Renderers

- `calendar_text`
- `weather_text`
- `train_departures_text`

## Output contract

- The rendered image is converted to Pillow mode `1` before MQTT publishing.
- The published payload must remain compatible with the firmware bitmap contract.
- MQTT publish failures surface as runtime errors.
