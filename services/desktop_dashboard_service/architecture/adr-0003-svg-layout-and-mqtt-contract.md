# ADR-0003: Use SVG text slots as the layout format and publish firmware-compatible MQTT payloads

## Status

Accepted

## Context

The service needs a human-editable layout format and must produce output that the firmware can consume without any additional transformation.

## Decision

- Dashboard layouts are authored as standard SVG templates.
- Renderers populate SVG elements by id, with the current implementation restricted to `<text>` elements.
- The composed SVG is rasterized and converted into the 1-bit payload required by the firmware.
- The same execution may also emit a preview image for local inspection.

## Consequences

- Layout editing stays accessible with standard SVG tooling.
- The service preserves a strict contract with the firmware output format.
- Non-text layout targets or richer rendering behaviour require an explicit architectural update.
