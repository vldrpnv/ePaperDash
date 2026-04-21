# ADR-003: Use CRC-32 for image change detection

- Status: Accepted
- Date: 2026-04-21

## Context

The display should only refresh when the image changes, because unnecessary ePaper refreshes cost time, power, and panel life.

## Decision

The firmware computes a CRC-32 over the incoming 48,000-byte image and compares it with the previous CRC before refreshing the display.

## Consequences

- Change detection is fast and small enough for the ESP32-C3.
- The checksum is suitable for refresh decisions, not for security or authenticity checks.
- The system accepts the small collision risk inherent in CRC-32.

## Evidence

- `ePaperDash.ino` implements `crc32()` and uses it before calling `showImage()`.
- `README.md` states that refreshes are skipped when the image CRC is unchanged.
