# Desktop dashboard service

Python service that builds dashboard images from pluggable data sources, renders them into an SVG layout, converts the result into the 1-bit payload expected by the firmware, and publishes it over MQTT.

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

- Static SVG content such as shapes, lines, and embedded images can be part of the template. For example, a weather icon or appliance image can be placed directly in the SVG with standard SVG elements such as `<image>`.
- The current plugin/rendering implementation populates text slots only. If you want source-driven images (for example, changing weather icons), the next step would be to add an image-capable renderer plugin and matching SVG slot handling.
- Text does not auto-fit to a box today. Font sizing comes from the SVG template (`font-size`) and can be overridden per panel through `renderer_config` for supported text attributes such as `font-size`, `font-family`, `font-weight`, `fill`, and `text-anchor`.
