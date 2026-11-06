# DD-008: Use MVG BGW-PT v3 API for Munich S-Bahn/MVV departure data

## Status

Accepted

Reviewed 2026-11-06: provider integration retained without external API revalidation. For the target, use [ADR-0007](adr-0007-shared-source-instances-and-view-specific-rendering.md) for station/query coverage and view-specific limits, and [ADR-0008](adr-0008-source-owned-freshness-and-failure-policy.md) for explicitly marked cached fallback. A fallback duration has not been chosen. The existing filename is historical; the decision body describes BGW-PT v3.

## Context

A new `mvg_departures` panel type needs real-time S-Bahn and MVV departure information for stations in the Munich metropolitan area.  The requirement is to show scheduled time, actual time (or cancelled status), and the line label for each upcoming departure at a user-configured station.

Several API options were considered, ranked by preference (MVV > DB > general):

| Option | Registration | Coverage | Stability |
|--------|-------------|----------|-----------|
| MVG BGW-PT v3 (`www.mvg.de/api/bgw-pt/v3`) | None | Munich S-Bahn, U-Bahn, Tram, Bus, regional MVV | Unofficial; widely used by community projects |
| DB Timetables / RIS Boards API | Required (developer.db.de) | Germany-wide including S-Bahn | Official but gated |
| Google Transit | Required | Variable | General-purpose |

## Decision

Use the unofficial MVG BGW-PT v3 REST API (`https://www.mvg.de/api/bgw-pt/v3/`) because:

1. It requires no registration, keeping setup friction near zero.
2. It is the closest data source to MVV (operated by the MVG transport company itself).
3. It is widely reverse-engineered and has remained stable across multiple years.
4. It provides real-time delay and cancellation data for the Munich area.

The `MvgDepartureSourcePlugin`:
1. Resolves the human-readable `station_name` from config to a `globalId` via `GET /locations?query=`.
2. Fetches departures via `GET /departures?globalId=&limit=&offsetInMinutes=` and includes a timezone preference query parameter when configured.
3. Handles both `plannedDepartureTime` as epoch milliseconds and as ISO-8601 strings (the API format may vary).
4. Handles both a bare JSON array response and a `{"departures": [...]}` wrapped response for resilience against API changes.
5. Normalizes parsed planned and realtime departure times to a configured IANA timezone (default: `Europe/Berlin`) before handing data to renderers.

Configuration keys: `station_name` (required), `limit` (default 5), `offset_minutes` (default 0), `timezone` (default `Europe/Berlin`), `base_url` (override for testing).

## Consequences

- No API key or registration step is required for operators.
- Because the API is unofficial, it may change without notice. Transient acquisition failures are mapped to `SourceUnavailableError` and isolated by the current panel-failure contract (ADR-0004); target fallback follows ADR-0008.
- Only the Munich MVG/MVV network is covered; different cities require a different source plugin.
