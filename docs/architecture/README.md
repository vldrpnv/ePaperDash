# Architecture knowledge base

This directory captures the current architectural and technical design decisions for `ePaperDash`, based on the repository code and the implementation history that introduced the firmware.

## Structure

- `adr/`: long-lived architectural decisions that shape the system.
- `design_decisions/`: lower-level technical decisions that guide implementation details.

## Evidence used

- `04b7650` — initial repository bootstrap.
- `ca9508f` — main firmware, configuration, and README implementation.
- `ee2d4db` — merge of the initial feature work.
- Current source files: `ePaperDash.ino`, `config.h`, `README.md`.

## ADR inventory

1. `ADR-001-use-mqtt-retained-images.md`
2. `ADR-002-use-deep-sleep-and-rtc-state.md`
3. `ADR-003-use-crc32-for-change-detection.md`
4. `ADR-004-use-a-one-shot-wake-render-sleep-cycle.md`
5. `ADR-005-allocate-the-image-buffer-per-cycle.md`
6. `ADR-006-use-gxepd2-with-a-configurable-display-model.md`

## Design decision inventory

1. `DD-001-keep-runtime-configuration-and-hardware-mapping-in-config-h.md`
2. `DD-002-use-staged-network-timeouts-and-sequencing.md`
3. `DD-003-validate-and-handle-mqtt-messages-in-a-single-callback.md`
4. `DD-004-enforce-a-strict-1-bit-image-contract-and-rendering-flow.md`
5. `DD-005-fail-safe-to-sleep-after-errors-or-missed-updates.md`
6. `DD-006-use-prefixed-serial-logs-for-observability.md`

## Working agreement

When behavior changes:

1. Capture or update the expected specification first.
2. Add or update tests before implementation when the change is testable.
3. Update the relevant ADR or design decision if the change alters intent, trade-offs, or constraints.
