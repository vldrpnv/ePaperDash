# DD-008: Use MVG FIB v2 API for Munich S-Bahn/MVV departure data

## Status

Accepted

## Context

A new `mvg_departures` panel type needs real-time S-Bahn and MVV departure information for stations in the Munich metropolitan area.  The requirement is to show scheduled time, actual time (or cancelled status), and the line label for each upcoming departure at a user-configured station.

Several API options were considered, ranked by preference (MVV > DB > general):

| Option | Registration | Coverage | Stability |
|--------|-------------|----------|-----------|
| MVG FIB v2 (`www.mvg.de/api/fib/v2`) | None | Munich S-Bahn, U-Bahn, Tram, Bus, regional MVV | Unofficial; widely used by community projects |
| DB Timetables / RIS Boards API | Required (developer.db.de) | Germany-wide including S-Bahn | Official but gated |
| Google Transit | Required | Variable | General-purpose |

## Decision

Use the unofficial MVG FIB v2 REST API (`https://www.mvg.de/api/fib/v2/`) because:

1. It requires no registration, keeping setup friction near zero.
2. It is the closest data source to MVV (operated by the MVG transport company itself).
3. It is widely reverse-engineered and has remained stable across multiple years.
4. It provides real-time delay and cancellation data for the Munich area.

The `MvgDepartureSourcePlugin`:
1. Resolves the human-readable `station_name` from config to a `globalId` via `GET /station?query=`.
2. Fetches departures via `GET /departure?globalId=&limit=&offsetInMinutes=` and includes a timezone preference query parameter when configured.
3. Handles both `plannedDepartureTime` as epoch milliseconds and as ISO-8601 strings (the API format may vary).
4. Handles both a bare JSON array response and a `{"departures": [...]}` wrapped response for resilience against API changes.
5. Normalizes parsed planned and realtime departure times to a configured IANA timezone (default: `Europe/Berlin`) before handing data to renderers.

Configuration keys: `station_name` (required), `limit` (default 5), `offset_minutes` (default 0), `timezone` (default `Europe/Berlin`), `base_url` (override for testing).

## Consequences

- No API key or registration step is required for operators.
- Because the API is unofficial, it may change without notice.  Network failures and unexpected response shapes are surfaced as runtime errors that cause the service to skip the cycle (per DD-005).
- Only the Munich MVG/MVV network is covered; different cities require a different source plugin.
