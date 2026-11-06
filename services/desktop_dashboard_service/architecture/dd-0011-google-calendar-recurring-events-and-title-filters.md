# DD-0011: Expand Google Calendar recurrence sets and filter unwanted titles

## Status

Accepted

Revised target scope, 2026-11-06: recurrence expansion and normalization remain source concerns. Under [ADR-0007](adr-0007-shared-source-instances-and-view-specific-rendering.md), display-day selection, visible limits, and presentation-only title exclusions may differ by view and must not truncate another consumer's shared data. Hard exclusions defining privacy/access scope remain source-side before sharing. The source filtering below is still the current implementation; migration and exact selection APIs remain open.

## Context

The Google Calendar dashboard panel is fed from an iCal source where many
entries are recurring. The previous implementation only evaluated the first
`DTSTART` instance, so later `RRULE` occurrences never appeared on the
dashboard. Users also need a lightweight way to suppress routine or private
calendar entries without changing the upstream calendar itself.

## Decision

- The `google_calendar` source expands the iCal recurrence set for the target
  local day.
- Recurrence expansion includes `RRULE` and `RDATE` occurrences and excludes
  instances listed in `EXDATE`.
- Title filtering is handled in the source through
  `source_config.blacklist_terms` (list of case-insensitive substrings) and
  `source_config.filter_word` (single-term shorthand).
- Filtering is applied before events are returned to renderers, so renderers
  and layout handling remain unchanged.

## Consequences

- Recurring calendar events now appear on the day they occur instead of only on
  their first `DTSTART`.
- Users can hide unwanted event categories with local source configuration.
- The change stays inside the source adapter and preserves the existing
  domain/rendering contracts.
