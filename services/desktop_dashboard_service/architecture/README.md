# Desktop dashboard service architecture

This directory captures the current specification and the design decisions for `services/desktop_dashboard_service`.

The [2026-11-06 decision revision](../../../architecture/decision-revision.md) records the multi-screen target. ADR-0007/0008 revise the target source and failure contracts; the legacy pipeline remains implemented until migration.

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
- `adr-0007-shared-source-instances-and-view-specific-rendering.md` — target shared acquisition with use-specific selection and rendering
- `adr-0008-source-owned-freshness-and-failure-policy.md` — target source-owned cache freshness and explicit unavailable/stale fallback
- `dd-0007-rich-text-spans-and-auto-font-size.md` — TextSpan / RichLine / StyledLine model and bbox auto-sizing heuristic
- `dd-0008-mvg-fib-v2-departure-source.md` — MVG BGW-PT v3 departure source (historical filename)
- `dd-0009-two-zone-grid-layout.md` — two-zone layout rationale (left rail + main content area)
- `dd-0010-dashboard-layout-specification.md` — complete region map, typography scale, icon sizes, and train-row state grammar
- `dd-0011-google-calendar-recurring-events-and-title-filters.md` — expand iCal recurrences and hide unwanted titles in the Google Calendar source
- `dd-0012-ffb-waste-collection-source-and-renderer.md` — AWIDO-backed waste collection source and compact three-day renderer
