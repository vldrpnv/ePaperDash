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
- Add a built-in `waste_collection_text` renderer that shows the next N entries
  (default 3, configurable via `max_entries`), emphasises today and tomorrow
  with bold larger text, formats the date as `"Sa, 02. Mai"` (weekday abbreviation
  + zero-padded day + German month abbreviation, no year), strips size/frequency
  suffixes from the waste-type name (e.g. `"Biotonne 60–240 Liter"` → `"Biotonne"`),
  and renders a no-collection message when no entries remain.
- Calendar items returned by AWIDO for public holidays carry `fr: null`; the
  source skips these entries rather than treating them as a fetch error.

## Consequences

- Fürstenfeldbruck/Eichenau waste data can be configured without changing the
  dashboard application flow or MQTT contract.
- The implementation remains text-slot based and reuses the existing rich-text
  span and per-line font-size support.
- The example layout dedicates the lower-left column to a stacked calendar +
  waste presentation; the waste panel stays compact by showing only the first
  word of each waste-type name and limiting output to `max_entries` rows.
- Public-holiday marker entries from AWIDO (null fraction list) are silently
  skipped and never reach the renderer.
