# ADR-0001: Organize the service with DDD-style models and hexagonal boundaries

## Status

Accepted

Reviewed 2026-11-06: retained as the organization direction. [ADR-0007](adr-0007-shared-source-instances-and-view-specific-rendering.md) and [ADR-0008](adr-0008-source-owned-freshness-and-failure-policy.md) add shared source identity and freshness responsibilities. Existing application imports of SVG adapter helpers and Pillow-dependent domain models mean dependency isolation is not fully enforced today; this revision does not claim otherwise.

## Context

The service combines configuration loading, third-party data acquisition, layout rendering, image encoding, and MQTT publishing. Those responsibilities will grow as more dashboard panels are added.

## Decision

The service is organized around a DDD-style and hexagonal split.

- `domain` contains the core models and port definitions.
- `application` coordinates use cases and plugin selection.
- `adapters` implement external concerns such as HTTP, SVG, and MQTT.
- `bootstrap` wires concrete adapters into the application service.

## Consequences

- Core orchestration stays independent from concrete source, renderer, layout, and publish technologies.
- New integrations should be added as adapters behind the existing ports.
- Changes that move responsibilities across these boundaries should update this ADR and the current specification.
