# ADR-002: Use deep sleep and RTC memory for short-lived state

- Status: Accepted
- Date: 2026-04-21

## Context

The device is battery-powered and only needs to check for updates periodically. It also needs to remember whether the last rendered image changed across wake cycles.

## Decision

The firmware performs one active cycle per wake, then enters deep sleep for `CHECK_INTERVAL_SEC`. It stores the previous image CRC in RTC memory with `RTC_DATA_ATTR`.

## Consequences

- Power use is minimized during idle periods.
- The last image CRC survives deep sleep, but not a full power loss.
- A full power cycle causes the next received image to be treated as new.

## Evidence

- `ePaperDash.ino` persists `lastImageCrc` in RTC memory and always ends the cycle in `goToSleep()`.
- `README.md` documents the periodic wake-check-sleep behavior.
