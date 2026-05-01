# DD-011: Use AWIDO customer `ffb` for Fürstenfeldbruck/Eichenau waste collection data

## Status

Accepted

## Context

The dashboard needs a waste-collection panel for AWB Landkreis Fürstenfeldbruck addresses in Eichenau. The operator must be able to configure an address and optionally limit the panel to one or more waste types, while the rendered output should focus only on imminent pickups in a three-day window starting today.

The existing service already supports pluggable sources and rich-text renderers. The new panel should reuse those extension points and avoid introducing a second rendering path.

## Decision

- Add a built-in `ffb_waste_collection` source plugin backed by the AWIDO customer `ffb` web-service endpoints.
- Resolve the configured address through the AWIDO place → street → house-number selectors, defaulting to `city = "Eichenau"` and accepting either:
  - `address`, or
  - `street` plus optional `house_number`
- Fetch collection events from the AWIDO calendar endpoint and normalize them into a waste-collection domain model containing:
  - `address_label`
  - `reference_date`
  - `entries[]` with `date` and `waste_type`
- Support optional `waste_type` or `waste_types` filtering in the source configuration.
- Add a built-in `waste_collection_text` renderer that:
  - keeps only entries due within a three-day window starting at the source reference date,
  - includes the waste type on each line,
  - renders tomorrow’s line in bold with a larger font,
  - renders a no-collection message when the three-day window is empty.

## Consequences

- Fürstenfeldbruck/Eichenau waste data can be configured without changing the dashboard application flow or MQTT contract.
- The implementation remains text-slot based and reuses the existing rich-text span and per-line font-size support.
- Address resolution is coupled to the AWIDO `ffb` customer configuration; if the upstream selector values change, the source must surface the issue as a configuration error or transient unavailability as appropriate.
