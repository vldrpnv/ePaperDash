# DD-001: Keep runtime configuration and hardware mapping in `config.h`

## Decision

User-editable settings and board-specific pin assignments are centralized in `config.h`.

## Rationale

- Keeps the sketch focused on behavior instead of deployment details.
- Makes WiFi, MQTT, timing, geometry, and control pins easy to customize before flashing.
- Reflects the Arduino workflow documented in `README.md`.

## Evidence

- `config.h` contains credentials, broker settings, timeouts, display geometry, and ePaper control pins.
