# DD-003: Validate and handle MQTT messages in a single callback

## Decision

All incoming MQTT messages are routed through one callback, which first verifies the topic and payload size before copying the image into the buffer.

## Rationale

- Matches the small subscription surface of the project.
- Rejects malformed updates early.
- Keeps the active runtime state simple: copy data, mark `imageReceived`, continue the main flow.

## Evidence

- `ePaperDash.ino` checks `MQTT_TOPIC_IMAGE`, validates `length == IMAGE_BYTES`, and then copies the payload.
