# Architecture decision revision

Date: 2026-11-06. Basis: the [project review](direction-review.md), [interview answers](direction-interview.md), and static inspection of the current implementation and all 28 existing ADR/design-decision records.

This revision records the target architecture. It does not implement a new runtime or configuration schema. The current specifications continue describing the implementation; revised records identify which parts remain current and which are replaced in the target.

## Revised direction

1. **Screen schedules select views.** Each screen has independent weekday/weekend and time-of-day rules. A selected view owns its layout and block assignments. See [repository ADR-0004](adr-0004-independent-screen-schedules-and-fixed-layout-views.md).
2. **Shared source instances supply reusable data.** Each use selects a subset and chooses a renderer. Acquisition coverage must support every consumer sharing the result. See [service ADR-0007](../services/desktop_dashboard_service/architecture/adr-0007-shared-source-instances-and-view-specific-rendering.md).
3. **Sources own freshness and fallback.** Valid cached data is reusable; unavailable is the preferred/default failure state, with explicitly marked stale fallback for source-specific exceptions. See [service ADR-0008](../services/desktop_dashboard_service/architecture/adr-0008-source-owned-freshness-and-failure-policy.md).
4. **Data changes stay inside fixed blocks.** Completing a trash task can change or suppress collection content. It does not remove the block, move surrounding blocks, or change assignments. Scheduled view changes can select a different layout.
5. **Retain the off-device renderer, MQTT delivery, and simple firmware.** Multiple outputs require isolated destinations; existing devices keep their current bitmap format. Different hardware support remains open.

These boundaries do not require microservices, a database, background polling, or a general workflow engine. Those mechanisms have not been selected.

## Disposition of existing decisions

“Retain” means the interview gives no reason to replace the architectural choice. It is not a hardware, external-provider, or performance revalidation. “Revise target” preserves the current implementation account while documenting its replacement direction.

### Repository and editor

| Existing record | Disposition | Effect |
| --- | --- | --- |
| [Repository ADR-0001: topology](adr-0001-system-topology.md) | Retain | Image generation stays off-device; extend output bindings for multiple screens. |
| [Repository ADR-0002: firmware cycle](adr-0002-firmware-refresh-cycle.md) | Retain | Device polling and source freshness are separate responsibilities. |
| [Repository ADR-0003: editor](adr-0003-config-editor-application.md) | Revise target | Edit screens, schedules, views, and sources as distinct concepts; correct claims about current preview/profile support. |
| [Editor ADR-0001: stack](../services/config_editor_app/architecture/adr-0001-architecture-and-tech-stack.md) | Retain stack; revise target | Keep Python/NiceGUI; faithful preview needs the production composition path. Activation/draft workflow remains proposed. |

### Dashboard service

| Existing record | Disposition | Effect |
| --- | --- | --- |
| [ADR-0001: boundaries](../services/desktop_dashboard_service/architecture/adr-0001-ddd-and-hexagonal-boundaries.md) | Retain | Put new source/view responsibilities behind clear boundaries; acknowledge current adapter coupling. |
| [ADR-0002: panel pipeline](../services/desktop_dashboard_service/architecture/adr-0002-plugin-panel-pipeline.md) | Revise target | ADR-0007 replaces panel-owned acquisition with source references and use-specific selection/rendering. |
| [ADR-0003: SVG/MQTT](../services/desktop_dashboard_service/architecture/adr-0003-svg-layout-and-mqtt-contract.md) | Retain; clarify | Record existing image composition and fixed-block target; preserve existing bitmap format. |
| [ADR-0004: slot clearing](../services/desktop_dashboard_service/architecture/adr-0004-source-failure-isolation-and-slot-clearing.md) | Revise target | Keep failure isolation; ADR-0008 replaces universal blanking with explicit availability and source-specific fallback. |
| [ADR-0005: publish recovery](../services/desktop_dashboard_service/architecture/adr-0005-bounded-mqtt-publish-retries-and-loop-recovery.md) | Retain | Bound retries; future multiple-output orchestration must avoid one failed output blocking the others. |
| [ADR-0006: weather](../services/desktop_dashboard_service/architecture/adr-0006-multi-provider-weather-and-precision-rendering.md) | Retain; refine scope | Preserve provider precision; separate acquisition coverage from each view's display coarsening/horizon. |
| [DD-0007: text fitting](../services/desktop_dashboard_service/architecture/dd-0007-rich-text-spans-and-auto-font-size.md) | Retain | Fit content within the block; do not change the layout geometry. |
| [DD-0008: MVG](../services/desktop_dashboard_service/architecture/dd-0008-mvg-fib-v2-departure-source.md) | Retain integration; revise policy | Shared queries need sufficient coverage; cached train fallback needs an explicit policy and visible stale state. |
| [DD-0009: two-zone layout](../services/desktop_dashboard_service/architecture/dd-0009-two-zone-grid-layout.md) | Narrow scope | Rationale for the example layout, not a universal dashboard grid. |
| [DD-0010: layout specification](../services/desktop_dashboard_service/architecture/dd-0010-dashboard-layout-specification.md) | Narrow scope; correct drift | Scope coordinates/typography to this template; correct the clock box and train-state text against current code/configuration. |
| [DD-0011: calendar filtering](../services/desktop_dashboard_service/architecture/dd-0011-google-calendar-recurring-events-and-title-filters.md) | Revise target | Keep source normalization/privacy boundaries; allow view-specific display selection without truncating shared coverage. |
| [DD-0012: waste collection](../services/desktop_dashboard_service/architecture/dd-0012-ffb-waste-collection-source-and-renderer.md) | Revise target | Keep provider integration; separate view selection and completion-state rendering. Completion-state storage remains open. |

### Firmware

| Existing record | Disposition | Effect |
| --- | --- | --- |
| [ADR-001: retained images](../docs/architecture/adr/ADR-001-use-mqtt-retained-images.md) | Retain | Each device receives its bound output topic. |
| [ADR-002: sleep/RTC](../docs/architecture/adr/ADR-002-use-deep-sleep-and-rtc-state.md) | Retain | No source acquisition or scheduling moves into firmware. |
| [ADR-003: CRC](../docs/architecture/adr/ADR-003-use-crc32-for-change-detection.md) | Retain | Compare final image bytes; CRC is not a data-freshness indicator. |
| [ADR-004: one-shot cycle](../docs/architecture/adr/ADR-004-use-a-one-shot-wake-render-sleep-cycle.md) | Retain | Multiple screens do not require a continuously running device loop. |
| [ADR-005: image buffer](../docs/architecture/adr/ADR-005-allocate-the-image-buffer-per-cycle.md) | Retain | No memory-lifecycle change required by the interview. |
| [ADR-006: GxEPD2](../docs/architecture/adr/ADR-006-use-gxepd2-with-a-configurable-display-model.md) | Retain | Additional hardware requirements remain open. |
| [DD-001: compile-time settings](../docs/architecture/design_decisions/DD-001-keep-runtime-configuration-and-hardware-mapping-in-config-h.md) | Retain | Distinct output bindings can use each device's configured topic; remote provisioning is not selected. |
| [DD-002: network timeouts](../docs/architecture/design_decisions/DD-002-use-staged-network-timeouts-and-sequencing.md) | Retain | Keep bounded device work. |
| [DD-003: MQTT validation](../docs/architecture/design_decisions/DD-003-validate-and-handle-mqtt-messages-in-a-single-callback.md) | Retain | Topic and size validation remain applicable to each bound output. |
| [DD-004: bitmap contract](../docs/architecture/design_decisions/DD-004-enforce-a-strict-1-bit-image-contract-and-rendering-flow.md) | Retain | Existing 800×480, MSB-first, 1-bit format stays unchanged. |
| [DD-005: sleep after errors](../docs/architecture/design_decisions/DD-005-fail-safe-to-sleep-after-errors-or-missed-updates.md) | Retain | Source fallback happens before image publication, independently of device recovery. |
| [DD-006: logs](../docs/architecture/design_decisions/DD-006-use-prefixed-serial-logs-for-observability.md) | Retain | No logging-stack change required. |

## Open decisions before implementation

| Question | Settled boundary | Still to choose |
| --- | --- | --- |
| Source checks | Source decides whether cached data is valid. | On-demand invocation, background timers, or both; concurrent request handling and cache persistence. |
| Rendering and publication | Screen wake does not define source freshness; schedules select views. | Composition/publish triggers, intervals, and how a schedule boundary reaches a sleeping device. |
| Schedule semantics | Independent weekday/weekend and time-of-day rules per screen. | Timezones, DST, midnight, conflicts, and missing-rule defaults. |
| Failure presentation | Prefer unavailable; allow marked stale fallback by source. | Per-source durations, maximum stale age, and visual language. |
| Configuration/editor | Distinct screen/view/source responsibilities; faithful preview remains the goal. | Schema/version migration, drafts, validation interface, activation/reload, rollback, and preview live-data behavior. |
| Completion state | Changes rendered content within a fixed assignment. | Action interface, persistence, collection identity, reset behavior, and sharing between screens. |
| Hardware/delivery | Preserve the existing device contract. | Other display formats, exact topic conventions, process topology, and any delivery acknowledgement requirement. |

## Proposed next work

Resolve scheduler edge cases and source/composition invocation first. Then design a versioned configuration and one small implementation trial using the room-temperature example: one source fixture, two screen schedules, floor-specific and all-room views, fixed blocks, and explicit availability states. Add contract tests for cache reuse, schedule selection, output isolation, and unchanged geometry before replacing the legacy pipeline.

Keep editor activation and state-changing actions as separate follow-up designs. The interview did not authorize a specific workflow for either. No runtime, deployment, firmware, or example configuration was changed in this documentation revision.

## Engineering basis

Validation: all 28 prior decision records are linked in the disposition above; all 70 architecture Markdown links and whitespace checks pass. The existing payload-polarity test passes (`1 passed`), supporting the specification correction to `1` black / `0` white; the train renderer suite also passes (`38 passed`), supporting the corrected train-state descriptions. This is documentation validation, not a test of the unimplemented target architecture.

Complex architecture revision completed against the interview and repository sources, with a check that confirmed requirements, implementation facts, and proposed mechanisms remain distinct. FPF source `4260875dd8bc` (mirror `0340dc5449d6`), A.7/A.11.OP; protocols v2.0 `434dffd98a51`, `ansea09/agent-skills-and-protocols` trusted cache, chunk-first. Gate used current cached copies because sandbox networking is disabled; no GitHub refresh was attempted. External provider behavior and physical hardware were not revalidated.
