# DD-009: Two-zone layout with left context rail and main content area

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
- large whitespace with no intentional grouping,
- heavy structural divider lines making the board feel like a form rather than a dashboard.

The goal is to make the existing information easier to scan and give the board a clear,
appliance-like appearance on e-paper.

## Decision

Introduce a two-zone layout:

### Left context rail (x 0–182, full height)

A narrow 182 px-wide rail holds low-frequency context and personality elements.
Zones are separated by whitespace, not by visible divider lines.

1. **Compact date** (`calendar` text slot, x=8, y=32, bbox 168×60) — baseline y=32 keeps
   the ascenders of a 28 px font on-screen (text top ≈ 11 px).  The date is readable but
   no longer dominates.
2. **Analog validity-window clock** (`analog_clock` image slot, x=51, y=100, 76×96) —
   `size_px=60`, `show_tick_marks=false` keeps the face small and quiet; the `approx`
   label (`ca. HH:MM`) communicates freshness without implying precision.
3. **Mascot / decorative image** (`image_pool` image slot, x=22, y=212, 130×130) —
   reduced from the original 200×148 placement; secondary and contained within the rail.

### Main content area (x 188–800)

The remaining 612 px-wide area contains the functional information:

1. **Weather block** (`weather_block` image slot, x=188, y=6, 606×200) — the weather
   renderer (today headline + forecast blocks + tomorrow row) anchors the top of the
   main area.  Its 200 px height leaves the lower half of the screen for transport.
2. **Transport timetable** (`trains` text slot, x=232, y=228, bbox 556×242) — below a
   single light gray separator at y=212.  A small train icon path is positioned at
   x≈192, y≈214, and the timetable text begins at x=232 to the right of the icon.

### Grid constants

| Constant | Value |
|---|---|
| Rail width | 182 px |
| Rail outer margin | 8 px |
| Rail inner width | 174 px |
| Main content left edge | 188 px |
| Weather/transport separator | y=212 |
| Weather slot | x=188, y=6, w=606, h=200 |
| Transport timetable slot | x=232, y=228, bbox w=556, h=242 |

### Removed elements

- The `last_update` debug timestamp slot is removed.  The clock validity window
  (`ca. HH:MM`) already communicates dashboard freshness.
- The full-height vertical divider and all horizontal rail dividers are removed.
  Zones are defined by spacing and alignment, not by visible walls.

### Transport departure emphasis

The `first-departure-font-size` renderer_config key renders the next (first) departure at a
larger size than subsequent departures, giving it visual emphasis without requiring a
separate heading row.

## Consequences

- The layout follows a deterministic grid; no element floats on an empty canvas.
- Weather is the unambiguous main anchor at the top of the main content area.
- The clock is visually quiet and communicates approximate time/freshness only.
- The date baseline is on-screen; capital ascenders are never clipped.
- Transport departures have more horizontal space (556 px bbox, 242 px tall) and the next
  departure is visually emphasized.
- The `test_visual_regression.py` weather block constants and test SVG helper have been
  updated to match the new slot positions.
- Three new tests cover the `first-departure-font-size` behaviour.
- The acceptance criterion in `current-specification.md` has been updated to reflect the
  two-zone proportions.
