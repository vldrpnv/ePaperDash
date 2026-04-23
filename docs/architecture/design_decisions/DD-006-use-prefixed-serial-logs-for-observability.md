# DD-006: Use prefixed serial logs for observability

## Decision

Runtime logging uses short, prefixed messages such as `[WiFi]`, `[MQTT]`, `[EPD]`, and `[ERROR]`.

## Rationale

- Makes serial traces easier to scan during bring-up and troubleshooting.
- Helps separate connectivity, rendering, and lifecycle events.
- Fits the lightweight debugging model typical for Arduino firmware.

## Evidence

- `ePaperDash.ino` consistently logs with module-style prefixes across the wake cycle.
