# ADR-005: Allocate the image buffer per cycle

- Status: Accepted
- Date: 2026-04-21

## Context

The incoming image is large enough to matter on a constrained device: 800 × 480 / 8 = 48,000 bytes.

## Decision

The firmware allocates the image buffer on the heap during the active cycle, uses it for message receipt and rendering, and frees it before going back to sleep.

## Consequences

- Active memory is only reserved when needed.
- Allocation failure must be handled explicitly.
- The design avoids keeping a large buffer around longer than necessary.

## Evidence

- `ePaperDash.ino` allocates the buffer with `malloc()`, checks for failure, and frees it in `goToSleep()`.
