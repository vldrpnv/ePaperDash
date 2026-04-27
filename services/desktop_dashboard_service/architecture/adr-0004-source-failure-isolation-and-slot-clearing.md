# ADR-0004: Isolate transient source failures per panel and clear unavailable slots

## Status

Accepted

## Context

The dashboard build composes multiple independent panels. In the current flow, a timeout or network error in any source plugin aborts the whole cycle, so no payload is produced. This makes the service brittle in real-world conditions where upstream APIs can intermittently fail.

When a panel cannot fetch fresh data, rendering that panel's stale template text is also misleading.

## Decision

- Introduce an explicit source-level transient failure contract via `SourceUnavailableError`.
- Source plugins map transient availability errors (timeout, connection, temporary upstream errors, malformed upstream payloads) to `SourceUnavailableError`.
- The application service catches `SourceUnavailableError` per panel, skips rendering for that panel, and continues with remaining panels.
- The application service passes skipped panel slots to the layout renderer as `cleared_slots`.
- The SVG layout renderer clears each unavailable `<text>` slot (empty text and no child tspans) before rasterization.
- Non-transient errors (misconfiguration, plugin wiring errors, and renderer/source type mismatches) continue to fail fast.

## Consequences

- A transient outage in one source no longer prevents publishing dashboards from healthy panels.
- Published dashboards avoid stale or misleading content for unavailable panels.
- Source adapters need to classify failures and raise `SourceUnavailableError` for transient cases.
- Layout port and implementation gain a `cleared_slots` contract surface.
