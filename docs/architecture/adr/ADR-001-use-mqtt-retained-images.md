# ADR-001: Use MQTT retained images for dashboard delivery

- Status: Accepted
- Date: 2026-04-21

## Context

The device sleeps between refresh cycles, so it cannot rely on a continuously open connection. The implementation needs a simple way to obtain the latest dashboard image immediately after waking up.

## Decision

The firmware connects to WiFi, connects to an MQTT broker, subscribes to `MQTT_TOPIC_IMAGE`, and waits briefly for a retained message carrying the latest image.

## Consequences

- The publisher is responsible for keeping the latest image retained on the broker.
- The device can wake, fetch the current state, and sleep again without maintaining a long-lived session.
- Delivery stays transport-oriented and decoupled from any dashboard renderer.

## Evidence

- `README.md` describes publishing a retained image and the wake/subscribe flow.
- `ePaperDash.ino` subscribes after connection and waits for the retained payload in `setup()`.
