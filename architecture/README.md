# Repository architecture

This directory captures the repository-level architecture, current specification, and the decisions that shape both the firmware and the companion desktop service.

## How to reproduce the development flow

1. Read `current-specification.md` to understand the current externally visible behaviour and integration contracts.
2. Read the ADRs in this directory to understand which design choices are intentional and should be preserved unless explicitly changed.
3. If the change touches the desktop service, also read `services/desktop_dashboard_service/architecture/` before designing the change.
4. When a change alters structure, responsibilities, or a contract, add or update an ADR before or alongside implementation.
5. Change tests first for behaviour changes, then implement, then update the affected specification documents.

## Contents

- `current-specification.md` — current repository-level system contract
- `adr-0001-system-topology.md` — device/service separation and MQTT integration boundary
- `adr-0002-firmware-refresh-cycle.md` — wake, poll, compare, refresh, and sleep device lifecycle
