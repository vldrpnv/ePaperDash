# Desktop dashboard service architecture

This directory captures the current specification and the design decisions for `services/desktop_dashboard_service`.

## How to reproduce the development flow

1. Read `current-specification.md` to understand the current service contract and extension points.
2. Read the ADRs before changing structure, plugin contracts, layout handling, or MQTT output.
3. Update or add a test before changing behaviour.
4. Update or add an ADR when the service architecture or its contracts change.
5. Update the current specification after the implementation and tests converge.

## Contents

- `current-specification.md` — current service behaviour and extension contracts
- `adr-0001-ddd-and-hexagonal-boundaries.md` — domain/application/adapter split and dependency direction
- `adr-0002-plugin-panel-pipeline.md` — panel-oriented source/renderer composition model
- `adr-0003-svg-layout-and-mqtt-contract.md` — SVG text-slot layout and firmware-compatible output contract
- `adr-0004-source-failure-isolation-and-slot-clearing.md` — isolate transient source failures to the affected panel and clear unavailable slots
- `adr-0005-bounded-mqtt-publish-retries-and-loop-recovery.md` — retry transient MQTT publish failures and keep the periodic loop running
- `adr-0006-multi-provider-weather-and-precision-rendering.md` — unify weather providers behind one timeline contract and precision-aware icon rendering
