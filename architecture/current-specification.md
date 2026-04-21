# Current specification

## Scope

The repository currently contains two cooperating parts:

- firmware for the Seeed Studio XIAO 7.5" ePaper Panel
- a Python desktop service that generates dashboard images and publishes them to MQTT

## System contract

- The firmware consumes a retained MQTT message containing a raw 1-bit, 800 × 480 bitmap payload.
- The payload size is fixed at 48,000 bytes.
- Bit value `0` is rendered as black and `1` as white.
- The desktop service is responsible for producing payloads that match that contract.

## Firmware behaviour

On every wake cycle the device:

1. initializes serial logging and allocates the image buffer
2. connects to Wi-Fi using credentials from `config.h`
3. connects to the configured MQTT broker
4. subscribes to `MQTT_TOPIC_IMAGE`
5. waits up to `MQTT_MESSAGE_TIMEOUT_MS` for the retained image payload
6. ignores payloads whose size does not match the display contract
7. computes a CRC over the received image and refreshes the display only when the CRC changed
8. disconnects networking and deep-sleeps for `CHECK_INTERVAL_SEC`

## Desktop service behaviour

The desktop service:

1. loads TOML configuration
2. resolves the SVG layout path and optional preview output path
3. fetches data through named source plugins
4. renders the source data through named renderer plugins
5. fills SVG `<text>` slots by element id
6. rasterizes the SVG to an image
7. converts the image to the firmware-compatible 1-bit payload
8. optionally writes a preview image
9. publishes the payload to MQTT

## Configuration surfaces

### Firmware

`config.h` defines:

- Wi-Fi credentials
- MQTT broker host, port, client id, optional credentials, and topic
- timing constants for Wi-Fi, MQTT, retained-message wait, and deep sleep
- display size and ePaper pin mapping

### Desktop service

`services/desktop_dashboard_service/examples/dashboard_config.toml` shows the current configuration shape:

- `[layout]` for SVG template, output size, and optional preview output
- `[mqtt]` for broker and publish settings
- `[[panels]]` for source/renderer/slot wiring and per-plugin configuration

## Non-functional constraints

- The firmware is optimized for low-power periodic refresh rather than continuous interaction.
- Display refreshes must be avoided when the image content is unchanged.
- The desktop service keeps source acquisition, rendering, layout composition, and publishing replaceable.
- Both sides must remain compatible through the MQTT bitmap contract.
