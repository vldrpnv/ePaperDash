# ADR-0002: Compose the dashboard from source/renderer pairs per panel

## Status

Accepted

## Context

The dashboard needs to combine heterogeneous data sources while keeping panel-specific configuration explicit and replaceable.

## Decision

Each dashboard panel is defined by a source plugin, a renderer plugin, and an SVG slot.

- Source plugins fetch typed domain data.
- Renderer plugins declare the domain type they support.
- The application service validates that the fetched data type matches the renderer contract.
- A renderer may emit one or more text blocks for the configured slot.

## Consequences

- Sources and renderers can be extended independently.
- Plugin wiring lives in configuration rather than hard-coded panel logic.
- Type mismatches fail fast during execution instead of rendering incorrect output.
