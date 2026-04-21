# ADR-0001: Keep image generation off-device and integrate through MQTT

## Status

Accepted

## Context

The target hardware is a low-power ePaper device with constrained memory and a fixed display format. Dashboard content may come from multiple external sources and may require richer rendering and image conversion than is practical on the device.

## Decision

The repository keeps dashboard image generation outside the microcontroller firmware.

- The device acts as a consumer of a retained MQTT image topic.
- Image composition, data fetching, and rendering live in a separate desktop service.
- The integration boundary between both parts is a fixed raw bitmap payload contract.

## Consequences

- Firmware stays small, deterministic, and focused on connectivity, change detection, and display refresh.
- Service-side logic can evolve independently as long as the MQTT payload contract remains stable.
- Architectural decisions must be documented in both this directory and the service architecture directory when cross-boundary behaviour changes.
