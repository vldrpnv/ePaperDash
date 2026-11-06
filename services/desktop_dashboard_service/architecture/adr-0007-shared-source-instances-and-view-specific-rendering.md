# ADR-0007: Share source instances and make data selection and rendering view-specific

## Status

Accepted target direction, 2026-11-06. Not implemented. Revises the panel-owned acquisition model in [ADR-0002](adr-0002-plugin-panel-pipeline.md).

## Context

The current application calls `fetch(panel.source_config)` for every panel. Reusing a plugin name therefore does not create a shared source instance. Acquisition parameters can also truncate or coarsen data before a second consumer can use it.

The required example has one all-room temperature source serving floor-specific views and a scheduled all-room view. Layout, selection, and presentation must be able to vary without creating independent copies of that source.

## Decision

- Distinguish a **source plugin type** from a configured **source instance**. The instance owns acquisition configuration, credentials/access scope, freshness decisions, and cached data.
- A view's block assignment references a source instance and specifies the selection and renderer settings for that use. It does not duplicate the source's credentials or freshness policy.
- Normalize provider data into a reusable result. A view selects/aggregates the relevant portion and renders it inside its assigned block. Whether selection is implemented as a separate function or within a renderer remains open.
- Rendering must not mutate the shared cached result or fetch from the provider itself.
- Preserve source/renderer compatibility checks and the domain/application/adapter separation. Validate references and supported data types before activating a configuration where possible; runtime checks remain necessary.
- Only share results with compatible account/access scope, location, acquisition query, coverage, and precision. The plugin name alone is insufficient identity.

For temperatures, source data includes all intended rooms and enough room identity to support floor selection. Floor membership configuration and its storage are still to be designed.

## Acquisition coverage versus display selection

One consumer's five-event limit or coarser weather display must not discard information needed by another consumer sharing that result. Source instances need declared coverage adequate for their consumers; fetching every possible record is not required.

Calendar recurrence expansion and provider normalization remain acquisition concerns. Display windows, item limits, and presentation-specific filtering belong to each use when the shared data has sufficient coverage. Hard exclusions that define a source's privacy/access scope remain enforced before sharing; this decision does not require pooling private data into a globally available cache.

## Alternatives

- **Copy source configuration into every panel:** rejected as the target model because it leaves shared identity and freshness ambiguous.
- **Share one rendered image per source:** insufficient; the same data must support different subsets and representations.
- **Share by plugin name:** rejected because different accounts, locations, and queries are different sources.

## Acceptance criteria for implementation

1. Two floor views and an all-room view can consume one configured temperature source.
2. Requests within that source's valid cache lifetime can reuse acquisition results across views without additional upstream fetches.
3. Rendering one view does not alter data observed by another view.
4. A consumer requiring unavailable coverage is rejected or served by an adequate acquisition configuration; it is not silently shown truncated data as complete.
5. Different credential/access scopes are not accidentally merged.

## Migration and open choices

The current `[[panels]]` schema remains the implemented format. Its migration to named source references needs an explicit compatibility/versioning decision. Process topology, concurrent request coordination, cache persistence, exact schemas, and selection APIs are not settled here.
