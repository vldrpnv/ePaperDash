# DD-009: Two-zone grid layout with left context rail and main content area

## Status

Accepted

## Context

The previous layout placed the date, clock, mascot, and weather/transport as free-positioned
elements on the 800×480 canvas without a consistent grid.  This resulted in:

- the date block being visually dominant relative to its informational value (font-size 48),
- the analog clock placed near the top center, making it feel like a focal element rather
  than a secondary validity indicator,
- the mascot occupying the top-right quadrant as an independent sticker-like image,
- weather and transport sharing the right column with no clear hierarchy,
- large whitespace with no intentional grouping.

The goal is to make the existing information easier to scan and give the board a clear,
appliance-like appearance on e-paper.

## Decision

Introduce a two-zone grid layout:

### Left context rail (x 0–182, full height)

A narrow 182 px-wide rail holds low-frequency context and personality elements:

1. **Compact date** (`calendar` text slot, x=8, y=12, bbox 166×78) — auto-sized or
   explicitly set to ~28 px.  The date is readable but no longer dominates.
2. **Analog validity-window clock** (`analog_clock` image slot, x=54, y=102, 82×108) —
   `size_px=72` keeps the face small and secondary; the `approx` label (`ca. HH:MM`)
   communicates freshness without implying precision.
3. **Mascot / decorative image** (`image_pool` image slot, x=17, y=220, 148×158) —
   the image is integrated into the rail and reduced from the original 200×148 top-right
   placement to a secondary decorative element.

Horizontal separator lines within the rail separate the three elements visually.

### Main content area (x 188–800)

The remaining 612 px-wide area contains the functional information:

1. **Weather block** (`weather_block` image slot, x=188, y=6, 606×285) — the weather
   renderer (today headline + forecast blocks + tomorrow row) anchors the top of the
   main area.  Its position and size make it the primary visual element.
2. **Transport timetable** (`trains` text slot, x=232, y=308, bbox 556×166) — below a
   horizontal separator at y=295.  A small train icon path is positioned at x≈192,
   y≈300, and the timetable text begins at x=232 to the right of the icon.

### Grid constants

| Constant | Value |
|---|---|
| Rail width | 182 px |
| Rail/main separator | x=182 |
| Rail outer margin | 8 px |
| Rail inner width | 174 px |
| Main content left edge | 188 px |
| Weather/transport separator | y=295 |
| Weather slot | x=188, y=6, w=606, h=285 |
| Transport timetable slot | x=232, y=308, bbox w=556, h=166 |

### Removed elements

The `last_update` debug timestamp slot is removed from the layout template.  The analog
clock validity window (`ca. HH:MM`) already communicates dashboard freshness.  Full
ISO-8601 timestamps are considered debug-level information not appropriate for the normal
display.

## Consequences

- The layout now follows a deterministic grid; no element floats on an empty canvas.
- Weather is the unambiguous main anchor at the top of the main content area.
- The clock is visually quiet and communicates approximate time/freshness only.
- The date is compact and secondary; the mascot is contained within the rail.
- Transport departures have more horizontal space (556 px bbox vs. 236 px previously),
  enabling longer German destination names without overflow.
- The `last_update` full timestamp is no longer rendered in normal mode.
- The `test_visual_regression.py` weather block constants and test SVG helper have been
  updated to match the new slot positions.
- The acceptance criterion in `current-specification.md` for slot column boundaries has
  been updated to reflect the new two-zone grid.
