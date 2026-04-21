# DD-002: Use staged network timeouts and sequencing

## Decision

The firmware performs network work in a fixed order: connect WiFi, connect MQTT, subscribe, then wait for the retained message. Each stage has its own timeout budget.

## Rationale

- Separates failure modes cleanly.
- Prevents the device from hanging indefinitely.
- Keeps the wake window bounded for power management.

## Evidence

- `config.h` defines independent WiFi, MQTT, and message wait timeouts.
- `ePaperDash.ino` implements the stages in `wifiConnect()`, `mqttConnect()`, and the retained-message wait loop in `setup()`.
