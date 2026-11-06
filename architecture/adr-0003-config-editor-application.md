# ADR-0003: Keep a Python configuration editor with a shared rendering path

## Status

Existing Python/NiceGUI application retained. Scope revised 2026-11-06 from the [direction interview](direction-interview.md). Multi-screen editing and faithful preview remain target work, not implemented capabilities.

## Context

The runtime currently loads one TOML layout, MQTT destination, and list of panels. Earlier editor notes described shared sources and profiles as though the runtime already supported them; it does not. The editor has source/profile display scaffolding, while its preview substitutes dummy “Preview” text rather than executing the real source/renderers.

The target adds independently scheduled screens, reusable views, shared source instances, and source-specific freshness/failure policies. Editing must preserve those distinct responsibilities.

## Decision

- Retain the Python application in `services/config_editor_app`, using NiceGUI and the root locked `uv` environment shared with the dashboard service.
- Keep configuration location selection through `DASHBOARD_CONFIG_PATH` and the existing example-file default for the current application.
- Target editing must distinguish shared source configuration from view-specific selection/rendering, screen schedules, and output bindings. Editing one view must not silently rewrite another view's source configuration.
- Share the production rendering path for faithful previews. The current dummy preview is a placeholder and does not validate rendered source content, cache states, or scheduled views.
- The target editor must be able to inspect the selected screen/view and a chosen schedule time. Choosing a preview time must not be confused with changing source acquisition timestamps.

## Proposed workflow: not yet decided

Draft editing → reference/type/layout validation → realistic preview → explicit activation/reload, with a recovery path, remains a proposal from the review. The interview did not settle draft storage, atomic activation, rollback, schema migration, or the public rendering interface between the applications.

Current behavior saves the configuration during preview refresh, and the publisher reads it only at startup. Saving is therefore neither an isolated draft operation nor activation of a running publisher. These gaps must be addressed before calling the target workflow complete.

## Consequences

The applications can reuse Python rendering code. Preview fidelity requires a shared composition path and explicit data/time inputs; merely using the same SVG rasterizer is insufficient. UI organization must follow the target architecture rather than treat each panel as an independent acquisition configuration.

See [the editor-specific ADR](../services/config_editor_app/architecture/adr-0001-architecture-and-tech-stack.md) and [the decision revision](decision-revision.md).
