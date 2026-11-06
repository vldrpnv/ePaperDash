# ADR-0005: Use bounded MQTT publish retries and cycle-loop recovery

## Status

Accepted

Reviewed 2026-11-06: retained. Multiple outputs will need bounded retries and failure handling that lets other outputs continue; the current single-output loop does not implement this. Composition/publish triggers and the mechanism for coordinating outputs remain open in [the revision](../../../architecture/decision-revision.md).

## Context

The service publishes one retained dashboard payload per cycle. A transient broker outage currently raises an exception from the MQTT adapter and stops the CLI loop, which makes the service unavailable until restarted.

## Decision

- Extend MQTT configuration with:
  - `publish_retry_attempts` (default `3`)
  - `publish_retry_delay_seconds` (default `1.0`)
- The MQTT publisher retries failed connect/publish attempts with a fixed delay and bounded attempt count.
- After each attempt, the publisher disconnects best-effort to ensure a clean reconnect on the next attempt.
- If all attempts fail, the publisher raises a runtime error.
- The CLI loop catches per-cycle runtime failures, logs them, and continues the next scheduled cycle.

## Consequences

- Short broker interruptions are absorbed without dropping the whole service process.
- Long outages still surface clear cycle failures while preserving continuous operation.
- Retry behavior is explicit and configurable per deployment.
