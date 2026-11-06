# ADR-0003: Use SVG text slots as the layout format and publish firmware-compatible MQTT payloads

## Status

Accepted

Reviewed 2026-11-06: retained with the scope clarification below and the fixed-view requirements in [repository ADR-0004](../../../architecture/adr-0004-independent-screen-schedules-and-fixed-layout-views.md). Multiple hardware formats remain open; the current device contract is unchanged.

## Context

The service needs a human-editable layout format and must produce output that the firmware can consume without any additional transformation.

## Decision

- Dashboard layouts are authored as standard SVG templates.
- Text renderers populate SVG `<text>` elements by id. Image renderers produce image placements composited onto the rasterized layout; SVG image-slot geometry is merged into renderer configuration by the current application.
- The composed SVG is rasterized and converted into the 1-bit payload required by the firmware.
- The same execution may also emit a preview image for local inspection.

## Consequences

- Layout editing stays accessible with standard SVG tooling.
- The service preserves a strict contract with the firmware output format.
- The current bitmap is 800×480, 48,000 bytes, row-major, MSB-first, with `1` black and `0` white; the encoder inverts Pillow mode `1` bytes accordingly.
- In the target, the selected view owns block geometry and source/renderer assignments. Renderers may change content within those blocks, not reflow the layout. Exact geometry/style precedence and validation remain implementation decisions.
