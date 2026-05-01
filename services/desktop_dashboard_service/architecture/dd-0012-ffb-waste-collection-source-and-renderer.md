# DD-0012: Use AWIDO customer `ffb` for Fürstenfeldbruck/Eichenau waste collection data

## Status

Accepted

## Context

The dashboard needs a waste-collection panel for AWB Landkreis Fürstenfeldbruck
addresses in Eichenau. The operator must be able to configure an address and
optionally limit the panel to one or more waste types, while the rendered output
should stay compact enough to share the lower-left column with Google Calendar.

## Decision

- Add a built-in `ffb_waste_collection` source plugin backed by the AWIDO
  customer `ffb` web-service endpoints.
- Resolve the configured address through the AWIDO place → street →
  house-number selectors, defaulting to `city = "Eichenau"` and accepting
  either `address` or `street` plus optional `house_number`.
- Fetch collection events from the AWIDO calendar endpoint and normalize them
  into a waste-collection domain model with `address_label`, `reference_date`,
  and `entries[]` containing `date` and `waste_type`.
- Support optional `waste_type` or `waste_types` filtering in the source
  configuration.
- Add a built-in `waste_collection_text` renderer that keeps only entries due
  within a short look-ahead window, emphasizes tomorrow with bold larger text,
  and renders a no-collection message when the window is empty.

## Consequences

- Fürstenfeldbruck/Eichenau waste data can be configured without changing the
  dashboard application flow or MQTT contract.
- The implementation remains text-slot based and reuses the existing rich-text
  span and per-line font-size support.
- The example layout now dedicates the lower-left column to a stacked calendar +
  waste presentation, so the waste panel must stay compact and readable at that
  width.
