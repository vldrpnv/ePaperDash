# ADR-0008: Let sources own freshness and explicit failure fallback

## Status

Accepted target direction, 2026-11-06. Not implemented. Revises the blanket slot-clearing policy in [ADR-0004](adr-0004-source-failure-isolation-and-slot-clearing.md).

## Context

Screens must not determine when upstream data is too old. A source decides whether its last successful fetch is recent enough to reuse or whether it needs to fetch again. The interview prefers unavailable output after most fetch failures, with exceptions such as cached train schedules that visibly indicate stale data.

## Decision

- Each configured source instance owns its freshness policy and cache state. A caller requests data; it does not override freshness based on the screen's wake or rendering interval.
- A valid cached result remains available data. Serving it from cache alone does not make it stale.
- When another fetch is required, the source attempts acquisition. A successful acquisition updates the cached value and acquisition time.
- After acquisition failure, the preferred/default policy returns an explicit **unavailable** state. A configured source-specific exception may return the last successful data as **stale**.
- Stale fallback must preserve the original successful acquisition time and report its stale state. A failed attempt must not make old data appear newly acquired.
- Renderer-facing results must carry availability/freshness information with the data. The concrete result type is to be designed. Renderers show unavailable or stale status within their assigned block, without changing layout geometry or assignments.
- Continue isolating transient source failures from unrelated content. Unknown plugins, invalid configuration, and type mismatches remain configuration/programming failures; they must not silently become stale success.

Train schedules are an example of an allowed fallback policy, not a blanket permission to show arbitrarily old departures. Cache duration, maximum stale age, and exact visual treatment must be defined for each source before implementation.

## Alternatives

- **Always clear failed-source slots:** replaced as the target default because unavailable is an explicit state and some sources need marked stale fallback.
- **Always use the last successful value:** rejected because most sources should show unavailable and stale data must not appear current.
- **Let each screen choose source TTL:** rejected; one source's shared cache needs source-owned freshness decisions.

## Acceptance criteria for implementation

1. With a fixed clock, requests within the valid cache interval reuse the same source result; expired data causes a fetch attempt when freshness is checked.
2. Default fetch failure produces unavailable content without stopping unrelated rendering.
3. A source configured for stale fallback can return cached data with a visible stale indication and unchanged successful-acquisition time.
4. With no usable cached value, stale fallback produces unavailable output.
5. A source's configured stale-age limit is enforced once that policy is specified.
6. Availability and completion-state changes do not change block geometry or assignments.

## Open decisions

The interview did not choose whether a data request, background timer, or both invoke the source's freshness check. It also did not choose dashboard composition/publish triggers, cache persistence, precise duration values, or the final unavailable/stale visual language. These remain explicit follow-up decisions; source ownership does not imply autonomous background polling.
