# ADR-0002: Use a wake-poll-refresh-sleep firmware cycle

## Status

Accepted

## Context

ePaper hardware benefits from infrequent refreshes, and the device is expected to run with low power usage. The dashboard image is published as a retained MQTT message, so the latest state is available immediately after subscription.

## Decision

The firmware uses a periodic wake cycle instead of a long-running always-connected loop.

- Wake from deep sleep or power-on
- Connect to Wi-Fi and MQTT
- Subscribe to the retained image topic
- Wait for at most a bounded interval for the payload
- Refresh only when the payload CRC changed
- Power down networking and return to deep sleep

## Consequences

- Power consumption is reduced.
- The firmware depends on retained MQTT messages for quick recovery of the latest dashboard state.
- The producer side should publish complete images atomically and keep the retained message available.
