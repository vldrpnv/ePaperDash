# Architecture knowledge base

This directory captures the current architectural and technical design decisions for `ePaperDash`.

## Structure

- `adr/`: long-lived architectural decisions that shape the system.
- `design_decisions/`: lower-level technical decisions that guide implementation details.

## ADR index

| Record | Summary | Load when |
| --- | --- | --- |
| `ADR-001-use-mqtt-retained-images.md` | Delivers the dashboard as a retained MQTT payload so a waking device can fetch the latest image immediately. | You are changing how the device receives updates or how publishers deliver dashboard data. |
| `ADR-002-use-deep-sleep-and-rtc-state.md` | Uses deep sleep between checks and RTC memory for short-lived state across wake cycles. | You are changing power behavior, persistence, wake cadence, or recovery across sleep cycles. |
| `ADR-003-use-crc32-for-change-detection.md` | Uses CRC-32 to decide whether an incoming image is new enough to refresh the panel. | You are changing image identity, deduplication, integrity checks, or refresh gating. |
| `ADR-004-use-a-one-shot-wake-render-sleep-cycle.md` | Keeps the firmware lifecycle as a single `setup()`-driven wake → work → sleep transaction. | You are restructuring control flow, adding long-lived runtime behavior, or changing retry strategy. |
| `ADR-005-allocate-the-image-buffer-per-cycle.md` | Allocates the 48,000-byte image buffer only during the active cycle, then frees it before sleep. | You are changing memory ownership, buffer lifetime, or large payload handling. |
| `ADR-006-use-gxepd2-with-a-configurable-display-model.md` | Uses GxEPD2 as the display abstraction with a documented alternate panel model. | You are changing display drivers, render primitives, or panel compatibility assumptions. |

## Design decision index

| Record | Summary | Load when |
| --- | --- | --- |
| `DD-001-keep-runtime-configuration-and-hardware-mapping-in-config-h.md` | Keeps deployment-time settings and board pin mappings in `config.h`. | You are changing configuration boundaries, adding settings, or moving hardware mappings. |
| `DD-002-use-staged-network-timeouts-and-sequencing.md` | Separates WiFi, MQTT, and retained-message wait stages with independent timeout budgets. | You are changing connection sequencing, timeouts, or active-window limits. |
| `DD-003-validate-and-handle-mqtt-messages-in-a-single-callback.md` | Handles MQTT updates in one callback that validates topic and payload size before copying data. | You are changing subscription structure, callback flow, or payload validation rules. |
| `DD-004-enforce-a-strict-1-bit-image-contract-and-rendering-flow.md` | Requires a raw 800 × 480, 1-bit bitmap and renders it with the current full-window paged flow. | You are changing the image contract, decoding, render path, or display data format. |
| `DD-005-fail-safe-to-sleep-after-errors-or-missed-updates.md` | Prefers bounded failure handling by logging, cleaning up, and retrying on the next scheduled wake. | You are changing retry behavior, error handling, or failure recovery. |
| `DD-006-use-prefixed-serial-logs-for-observability.md` | Uses short prefixed serial logs to keep wake-cycle diagnostics readable. | You are changing logging format, observability, or troubleshooting workflow. |

## Working agreement

When behavior changes:

1. Capture or update the expected specification first.
2. Add or update tests before implementation when the change is testable.
3. Update the relevant ADR or design decision if the change alters intent, trade-offs, or constraints.
