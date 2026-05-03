# DD-013: Content-pressure modes — score calculation and adaptive display

## Status

Accepted

## Context

The 800×480 monochrome dashboard serves as a household operations board.  As
more information sources were added (weather, calendar, waste, transport, Trello)
the display began to feel visually overfull.  Widgets competed for space equally
even though their operational urgency differed greatly.

A static layout treats all widgets as equally important regardless of how much
real information is present on a given day.  A family planning day with many
calendar events, a weather warning, and a waste collection due tomorrow is very
different from a quiet Sunday with no events.

## Decision

Introduce a **content-pressure score** computed once per render cycle, before any
rendering takes place.  The score is a weighted sum of contributing factors.  The
score is then mapped deterministically to one of three **display modes** — *calm*,
*normal*, or *overloaded* — which downstream renderers and the layout can use to
decide what to show and how much.

The score and mode calculation live in
`domain/content_pressure.py` as pure functions with no I/O dependencies, making
them trivially testable and decoupled from rendering.

## Score weights

| Factor | Points |
|---|---|
| Calendar event today or tomorrow | 2 per event |
| Calendar event later in the week | 1 per event |
| Trello / task card | 1 per card |
| Severe weather warning present | 4 |
| Rain or storm forecast for tomorrow | 3 |
| Waste collection due within 48 h | 2 |
| Train delay or cancellation present | 4 |
| More than 5 upcoming departures | 1 |

## Mode thresholds

| Mode | Score range | Purpose |
|---|---|---|
| `calm` | 0 – 5 | Pleasant overview; decorative elements permitted |
| `normal` | 6 – 12 | Daily operations; decorative elements hidden |
| `overloaded` | ≥ 13 | Protect readability; minimum viable information only |

## Display rules per mode

### Analog clock

| Mode | Behaviour |
|---|---|
| `calm` | Analog clock face shown (size ≈ 90–140 px) with `ca. HH:MM` label |
| `normal` | Clock slot cleared; freshness communicated by date block only |
| `overloaded` | Clock slot cleared |

### Mascot / decorative image

| Mode | Behaviour |
|---|---|
| `calm` | Shown in lower left rail |
| `normal` | Hidden |
| `overloaded` | Hidden |

### Weather block

| Mode | Behaviour |
|---|---|
| `calm` | Expanded — 3 rows: today overview, 4-h blocks, tomorrow row |
| `normal` | Compact — today + tomorrow summary only |
| `overloaded` | Risk-only — one line, temperature range + condition |

### Trello / top tasks

| Mode | Max visible cards |
|---|---|
| `calm` | 5 |
| `normal` | 3 |
| `overloaded` | 2 |

### Calendar

| Mode | Behaviour |
|---|---|
| `calm` | Today + tomorrow detailed; later week detailed |
| `normal` | Today + tomorrow detailed; later week as summary counts |
| `overloaded` | Today detailed; tomorrow compact; later week as counts only |

### Waste collection

| Mode | Behaviour |
|---|---|
| `calm` | Next 3 collections |
| `normal` | Next 1–2 collections |
| `overloaded` | Next collection only |

### Transport

Transport is always visible in all modes with at least 4 departures.

---

## Consequences

### Positive

- The dashboard degrades predictably under content pressure.
- Decorative elements (clock, mascot) never displace operational information.
- The priority contract is explicit, deterministic, and testable.
- Score and mode selection are pure functions — no side effects, easy to unit test.
- Renderers can read the mode from a shared context; the mode can be overridden
  in config for automated testing.

### Negative

- Renderers must be updated one-by-one to respect the selected mode.
- The score inputs must be extracted from each source's output before rendering;
  this requires a lightweight summary pass.

---

## Relationship to other records

| Record | Relationship |
|---|---|
| DD-010 | The layout bounding boxes are the stable spatial contract; this record governs **what** is shown in each region, not where the region is. |
| DD-009 | Two-zone grid layout foundation; content pressure operates within it. |
| ADR-0002 | Plugin pipeline; the mode is threaded through the pipeline as a shared context value, not a plugin-level concern. |
