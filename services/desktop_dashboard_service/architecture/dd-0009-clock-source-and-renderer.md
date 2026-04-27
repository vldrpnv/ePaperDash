# DD-0009 — Clock source and renderer plugins

## Status

Accepted

## Context

The dashboard layout has usable space in the top portion of the right column
(x 310–580, y 0–163) that is not occupied by any existing panel.  A live
wall-clock display is a natural candidate for that area and requires no
external API calls.

## Decision

Introduce two new built-in plugins:

### `clock` source plugin

- Returns a `ClockTime` domain object wrapping a timezone-aware `datetime`.
- `source_config.timezone` accepts any IANA timezone name; defaults to `UTC`.
- Because the time is read from the local clock, the source is always
  available and never raises `SourceUnavailableError`.

### `clock_text` renderer plugin

- Accepts a `ClockTime` and emits a single `DashboardTextBlock`.
- `renderer_config.time_format` is a Python `strftime` pattern; defaults to
  `%H:%M`.
- SVG text attributes (`font-size`, `font-family`, `font-weight`, `fill`,
  `text-anchor`) are passed through from `renderer_config` to the target
  `<text>` element, consistent with the pattern established by
  `calendar_text` and `train_departures_text`.

### Layout slot

The example `layout.svg` adds `<text id="clock" x="310" y="100" …>` in the
top area of the right column, with a `data-bbox-width="270"` /
`data-bbox-height="120"` bounding box so the auto-font-size feature keeps the
time legible without overflowing.

### Config example

```toml
[[panels]]
source = "clock"
renderer = "clock_text"
slot = "clock"
[panels.source_config]
timezone = "Europe/Berlin"
[panels.renderer_config]
font-size = "72"
font-weight = "700"
```

## Consequences

- The clock panel is wired through the same source → renderer → slot pipeline
  as every other panel; no changes are needed to the application service or
  layout renderer.
- The `ClockTime` model is added to `domain/models.py` alongside the other
  domain data objects.
- Both plugins are registered in `bootstrap.py`; they are opt-in through
  `[[panels]]` configuration and have no effect when absent from the config.
- The `clock` slot in the example layout occupies x 310–580, y 0–163, which
  does not overlap with `image_pool` (x 590–790, y 10–158), `weather_block`
  (x 310–792, y 163–475), or `trains` (x 64–300).
