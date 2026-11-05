# ADR 0003: Configuration Editor Application

## Context

The `desktop_dashboard_service` uses a TOML file to configure shared data sources, time-of-day layouts, and panel rendering slots. As the complexity of the configuration increases, it becomes challenging for users to edit the file by hand without making syntax errors or incorrectly linking source IDs. Furthermore, it is difficult to visualize how configuration changes impact the actual ePaper display without fully restarting the service and waiting for an MQTT publish cycle.

A requirement was formulated to introduce a web-based, Python-backed editor application that allows WYSIWYCG (What You See Is What You Can Get) editing of the dashboard profiles, sources, and renderer settings, with realistic live previews.

## Decision

We will introduce a new service located at `services/config_editor_app`.

1. **Language & Stack:** The service will be written in Python to maintain consistency with the existing desktop service.
2. **Framework:** We will use **NiceGUI**, a Python framework built on FastAPI and Vue.js, to provide the interactive web forms and preview display without writing custom JavaScript frontend code.
3. **Live Preview:** The configuration editor depends directly on the core rendering logic of `desktop_dashboard_service`. The root `uv` project installs both local packages together; the editor uses the service's SVG rasterizer to generate a real-time PNG preview for the browser.
4. **Configuration Location:** The editor will locate `dashboard_config.toml` via the `DASHBOARD_CONFIG_PATH` environment variable, defaulting to the repository's example configuration.

## Consequences

- **Positive:** Users can visually verify changes to dashboard layout sizes, texts, and active profiles before deploying them.
- **Positive:** The editor remains entirely in the Python ecosystem.
- **Negative:** `config_editor_app` is closely coupled to the internals of `desktop_dashboard_service`. If the internal domain models or rendering pipelines of the dashboard service change significantly, the editor application may need corresponding updates.
- **Update:** The repository root now manages the editor and dashboard publisher in one locked `uv` environment, so they share a single Python installation.
