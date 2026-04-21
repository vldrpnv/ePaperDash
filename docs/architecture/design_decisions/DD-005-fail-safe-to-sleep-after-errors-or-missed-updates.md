# DD-005: Fail safe to sleep after errors or missed updates

## Decision

When setup cannot allocate memory, connect, subscribe, or receive an image in time, the device logs the issue, cleans up, and returns to sleep rather than retrying aggressively.

## Rationale

- Preserves battery life.
- Avoids long-lived failure loops on constrained hardware.
- Uses the next scheduled wake as the retry point.

## Evidence

- `ePaperDash.ino` goes back to sleep after allocation failure and after the normal flow regardless of whether an image was received.
