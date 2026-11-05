# ADR 0001: Architecture and Tech Stack

## Context

We need to build a web-based configuration editor for the ePaper dashboard system. It needs to provide a WYSIWYCG experience, meaning users can edit configuration values (like layout sources, text fields, or icons) and instantly see a realistic rendering of what the display will look like. The constraint is to remain entirely within the Python ecosystem.

## Decision

1. **Web Framework:** We will use [NiceGUI](https://nicegui.io/). NiceGUI allows us to build interactive web applications entirely in Python. It handles the client-server communication via WebSockets automatically, making live-updating previews straightforward to implement.
2. **Preview Generation:** To provide a realistic preview, we will not attempt to rewrite the SVG parsing and rendering logic in the browser. Instead, the root `uv` project installs `config_editor_app` and `desktop_dashboard_service` together from their local source paths. The editor instantiates the dashboard service's rendering pipeline (`cairosvg`, `Pillow`) in-memory to generate PNG images based on the temporary editor state, and serves those PNGs back to the NiceGUI frontend.
3. **Data Model:** The application state will mirror the structure of `dashboard_config.toml` (Layout, MQTT, Sources, Profiles). We will use `tomlkit` or the standard library `tomllib`/external `tomli` paired with a TOML writer to preserve comments and structure as much as possible when saving.

## Consequences

- **Positive:** True WYSIWYCG realistic preview since the actual service rendering code is used.
- **Positive:** Fast development speed without needing a separate frontend build pipeline (Node.js/npm).
- **Negative:** Generating PNGs on the server for every keystroke or slider change might be resource-intensive; we may need to introduce debouncing on input fields that trigger a re-render.
