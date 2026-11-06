# ADR-0001: Retain NiceGUI and align editing with the shared runtime model

## Status

Python/NiceGUI stack retained. Architecture scope revised 2026-11-06. Target editing and preview capabilities below are not implemented. Workflow choices remain proposed where identified.

## Current implementation

- The root `uv` environment installs the editor and dashboard packages together.
- `ConfigManager` reads and writes TOML with `tomlkit`.
- The UI edits basic layout/MQTT fields and lists panel, source, and profile entries where present. Shared sources and profiles are not supported by the current runtime configuration loader.
- Preview uses the service's SVG rasterizer but dummy text in place of actual plugin output. It is not a faithful dashboard preview.
- Refreshing the preview saves the file. The running publisher does not reload that file automatically.

## Revised target decision

Follow [repository ADR-0003](../../../architecture/adr-0003-config-editor-application.md) and [ADR-0004](../../../architecture/adr-0004-independent-screen-schedules-and-fixed-layout-views.md):

1. Retain NiceGUI and Python code reuse; no frontend-stack change is required by the interview.
2. Represent source instances separately from views, block selection/rendering, and independently scheduled screens. Do not mirror the legacy panel-owned source model as the target domain model.
3. Use the production composition/rendering path for faithful preview, with an explicitly selected screen/view, schedule time, and data inputs. Make unavailable/stale results visible without changing block geometry.
4. Keep source freshness ownership in the source layer. Preview/render code must not invent new acquisition times or override source TTL based on the selected screen.

## Proposed implementation work

A stable rendering entry point, recorded/fixture data for deterministic previews, isolated drafts, validation, and explicit activation/reload are candidates for closing current gaps. Exact API, draft persistence, live-fetch behavior, activation, and rollback have not been selected. This record does not claim the user approved those workflows during the interview.

## Consequences

Sharing the rasterizer alone is insufficient for WYSIWYCG fidelity. The editor and runtime must use the same interpretation of schedules, source references, selections, renderers, and availability states. Comment-preserving TOML editing remains useful, but the next schema and migration behavior need their own decision before implementation.
