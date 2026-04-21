# Desktop dashboard service

Python service that builds dashboard images from pluggable data sources, renders them into an SVG layout, converts the result into the 1-bit payload expected by the firmware, and publishes it over MQTT.

Architecture notes, ADRs, and the current specification live in `architecture/`.

## Highlights

- Python 3.12 service with domain-driven and hexagonal structure
- SVG layout templates
- Plugin-based source and renderer registries
- Initial source plugins:
  - calendar
  - weather forecast (Open-Meteo)
- Initial renderer plugins:
  - calendar_text
  - weather_text
- MQTT publisher compatible with the firmware topic payload

## Quick start

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .[dev]
epaper-dashboard-service --config examples/dashboard_config.toml
```

## Configuration

The service uses TOML. See `examples/dashboard_config.toml`.

- `layout.template`: SVG file path
- `layout.preview_output`: optional PNG preview path
- `layout.width` / `layout.height`: output size
- `mqtt.*`: MQTT publish settings
- `[[panels]]`: one panel per source plugin

Each panel selects:

- `source`: source plugin name
- `renderer`: renderer plugin name
- `slot`: SVG text element id to populate
- `source_config`: source plugin configuration
- `renderer_config`: renderer plugin configuration

## Layouts

The layout template is standard SVG. Each renderer writes text into a `<text>` element identified by the configured `slot`.
