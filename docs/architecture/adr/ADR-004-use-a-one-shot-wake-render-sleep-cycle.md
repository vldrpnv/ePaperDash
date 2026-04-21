# ADR-004: Use a one-shot wake-render-sleep cycle

- Status: Accepted
- Date: 2026-04-21

## Context

The firmware has a single responsibility: wake up, check for an updated image, optionally render it, and return to sleep.

## Decision

All operational logic lives in `setup()`. `loop()` remains empty because each wake cycle is treated as a complete unit of work.

## Consequences

- Control flow stays simple and restart-friendly.
- Failure handling becomes straightforward: log the problem and sleep until the next cycle.
- The design favors deterministic startup behavior over a continuously running event loop.

## Evidence

- `ePaperDash.ino` places the runtime flow in `setup()` and documents that `loop()` is never reached.
