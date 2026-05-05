# DD-010: Dashboard layout specification — regions, typography, icons, and train states

## Status

Accepted

## Context

DD-009 introduced the two-zone layout and documented the grid constants and the
delayed-departure display format.  It did not provide a single reference for:

- the complete named-region map with bounding boxes,
- the full typography scale,
- icon size budgets,
- or the complete visual grammar for all four train-row states.

This record captures those details so layout editors, renderer authors, and reviewers
have one authoritative reference for the visual contract.

---

## Canvas

| Property   | Value                          |
|------------|-------------------------------|
| Width      | 800 px                        |
| Height     | 480 px                        |
| Bit depth  | 1-bit (black / white)         |
| Viewing distance | 1–2 m               |
| Minimum legible text | 16 px at 1 m      |

---

## Named regions and bounding boxes

### Zone map

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│  RAIL (0–182)   │  MAIN (188–800)                                               │
│                 │                                                                 │
│  DATE           │  WEATHER (compact strip)                                       │
│  (8,0,168,68)   │  (188,6,604,72)                                               │
│                 │                                                                 │
│  CLOCK          │ ─── SEPARATOR (y=82, x=192–794) ────────────────────────────  │
│  (14,100,154,174)│                                                                │
│                 │  TRELLO (524,86,264,110)                                       │
│                 │                                                                 │
│  WASTE          │  GCAL BLOCK (196,198,596,124)                                 │
│  (8,304,168,60) │                                                                 │
│                 │  TRAINS (244,340,548,130)                                      │
│  MASCOT         │                                                                 │
│  (28,374,120,106)│                                                               │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Region table

Each row is `(x, y, width, height)` — origin at top-left corner of the region's content
box, not the glyph baseline.

| Region ID       | Slot / element     | x   | y   | w   | h   | Priority   |
|-----------------|--------------------|-----|-----|-----|-----|------------|
| `DATE`          | `calendar` text    |   8 |   0 | 168 |  68 | secondary  |
| `CLOCK`         | `analog_clock` img |  14 | 100 | 154 | 174 | tertiary   |
| `WASTE`         | `waste` text       |   8 | 304 | 168 |  60 | secondary  |
| `MASCOT`        | `image_pool` img   |  28 | 374 | 120 | 106 | tertiary   |
| `WEATHER`       | `weather_block` img| 188 |   6 | 604 |  72 | primary    |
| `SEPARATOR`     | `<line>` element   | 192 |  82 | 602 |   1 | structural |
| `TRELLO`        | `trello` text      | 524 |  86 | 264 | 110 | secondary  |
| `GCAL`          | `gcal_events`      | 196 | 198 | 596 | 124 | secondary  |
| `TRAIN_ICON`    | `<path>` element   | 196 | 334 |  44 |  54 | structural |
| `TRANSPORT`     | `trains` text      | 244 | 340 | 548 | 130 | primary    |

Notes:
- The DATE text baseline is `y=32`; the region box starts at `y=0` to include ascenders.
- CLOCK is `size_px=140`; the 154×174 image slot leaves enough room for the
  `ca. HH:MM` label while freeing the lower rail for waste collection.
  In *normal* and *overloaded* content-pressure modes, the CLOCK slot is cleared and
  only the date text remains; see DD-013 for the mode contract.
- WEATHER is now a compact 72 px-tall strip (was 168 px) to leave room for the
  information columns below.  The horizontal separator moves up to y=82 accordingly.
- TRELLO moves to the upper-right column (x 524–788, y 86–196), directly below the
  weather strip.  This frees the full bottom row for TRANSPORT.
- WASTE moves into the rail so the main area can devote one flexible block to
  the multi-day calendar renderer.
- TRANSPORT is now full-width in the lower row (width 548, x 244–792).
  There is no longer a vertical divider or a Trello column in the same row.
- TRANSPORT bottom edge is `y=470`, leaving a 10 px margin from the canvas bottom.
- TRAIN_ICON top-left is at `(196, 334)`; TRANSPORT text starts at `x=244`.
- The gutter between RAIL and MAIN is 5 px (x=183–187); it is intentionally empty.
- No visible dividers separate regions within the rail; whitespace alone defines zones.
- MASCOT is shown only in *calm* content-pressure mode; see DD-013.

### Transport column layout (within TRANSPORT slot)

The timetable uses three implicit fixed-width columns.  All coordinates are
absolute (canvas-relative).

| Column           | Left edge (x) | Nominal width | Right edge (x) |
|------------------|--------------|---------------|----------------|
| Departure time   | 244          | 72 px         | 316            |
| Destination      | 328          | 196 px        | 524            |

---

## Typography scale

Fonts are proportional sans-serif (Arial / DejaVu Sans) throughout.
All sizes are nominal SVG/PIL pixel values at the 800×480 canvas resolution.

| Role                              | Region        | Size (px) | Weight | Style   |
|-----------------------------------|---------------|-----------|--------|---------|
| Date — day-of-week (line 1)       | DATE          | 22        | 700    | normal  |
| Date — day + month (line 2)       | DATE          | 26        | 700    | normal  |
| Clock validity label `ca. HH:MM`  | CLOCK (below) | 11        | 400    | normal  |
| Weather — today temperature range | WEATHER row 1 | 38        | 700    | normal  |
| Weather — today condition label   | WEATHER row 1 | 20        | 400    | normal  |
| Weather — forecast block time     | WEATHER row 2 | 14        | 400    | normal  |
| Weather — forecast block temp     | WEATHER row 2 | 18        | 700    | normal  |
| Weather — tomorrow label          | WEATHER row 3 | 16        | 400    | normal  |
| Google Calendar — day label       | GCAL          | auto¹     | 700    | normal  |
| Google Calendar — event text      | GCAL          | auto¹     | 400    | normal  |
| Waste collection — body           | WASTE         | 13        | 400    | normal  |
| Waste collection — today/tomorrow | WASTE         | 15        | 700    | normal  |
| Transport — station name          | TRANSPORT     | 20        | 700    | normal  |
| Transport — time                  | TRANSPORT     | 16        | 400    | normal  |
| Transport — destination           | TRANSPORT     | 16        | 400    | normal  |
| Trello — list header              | TRELLO        | auto²     | 700    | normal  |
| Trello — card name                | TRELLO        | auto²     | 400    | normal  |

¹ GCAL font is auto-sized to fit all visible events in the image height.

² TRELLO font is auto-sized via `data-bbox-width="250"` and `data-bbox-height="130"`.
`font-size` in `renderer_config` (default 14) sets the nominal size; the SVG renderer
reduces it automatically when content overflows the bounding box.
`font-size` in `renderer_config` (default 14) acts as an upper bound; the
renderer shrinks it so that `ceil(n_events / 2)` rows fit within the slot
height using the formula `min(font-size, floor(height / (rows_per_col × 1.3)))`.
Day labels use the bold variant of the same auto-sized font.

Sizing rule: the TRANSPORT slot declares `data-bbox-width="280"` and
`data-bbox-height="130"`.  The auto-fit heuristic sizes the overall block first;
`departure-font-size` in `renderer_config` overrides the computed size (see DD-007).
`station-name-font-size` sets the station header size independently via `StyledLine`.
Line designations ("S1", "S3") are hidden by default (`show-line = false`).

---

## Icon sizes

All icons are monochrome (black on white) to remain valid in 1-bit output.

### Weather icons (inside WEATHER `weather_block` image slot)

| Row                  | Icon role              | Size (px) | Notes                           |
|----------------------|------------------------|-----------|----------------------------------|
| Row 1 — today        | Condition headline     | 56        | `icon_size_factor` in config    |
| Row 2 — 4-hour block | Forecast block icon    | 28        | Three blocks, equal size        |
| Row 3 — tomorrow     | Tomorrow condition     | 32        | `tomorrow_icon_size_factor`     |

### Structural icons

| Element            | Size          | Notes                                       |
|--------------------|---------------|---------------------------------------------|
| TRAIN_ICON path    | ~35 × 46 px   | SVG path scaled by 0.2 from 256×256 viewBox |

---

## Train row states

Each departure row occupies one logical line within the TRANSPORT slot.  The
NEXT departure (topmost row) receives larger type; subsequent rows are uniform.

### Column notation

`[LINE]` `[TIME]` `[DESTINATION]`

### State: next

All departures are rendered at the same size.  The first row in the list
is implicitly "next" by position; no size or label distinction is applied.

```
[TIME 400 20px]    [DESTINATION 400 20px]

17:42              München Hbf
```

- TIME: normal weight, 20 px
- DESTINATION: normal weight, 20 px
- Vertical spacing after first row: `dy="1.4em"`

### State: normal

```
[TIME 400 20px]    [DESTINATION 400 20px]

17:51              Grafrath
```

- Uniform 20 px, no line label.
- Vertical spacing: `dy="1.2em"`.

### State: delayed

Scheduled time is struck through; bold offset indicator follows.

```
[~~TIME~~ 400 20px  +Xm 700 20px]    [DESTINATION 400 20px]

~~17:59~~  +4m                        München Hbf
```

Rendered as a `RichLine` / `StyledLine`:
- TIME span: `strikethrough=True`
- `+Xm` span: `bold=True`
- DESTINATION: plain span, normal weight
- No second full time value is shown (prevents two `HH:MM` values from
  appearing side-by-side and colliding).

### State: cancelled

All content is struck through to communicate the row is void.

```
[~~TIME~~]    [~~DESTINATION~~]

~~18:03~~     ~~München Hbf~~
```

Rendered as a `RichLine` where every span has `strikethrough=True`.
The entire row is visually subordinate; readers skip it instantly.

### State summary table

| State     | TIME style      | DESTINATION style | Size |
|-----------|-----------------|-------------------|------|
| next      | normal, plain   | normal, plain     | 20px |
| normal    | normal, plain   | normal, plain     | 20px |
| delayed   | normal, ~~s/t~~ + **+Xm** bold | normal, plain | 20px |
| cancelled | ~~s/t~~         | ~~s/t~~           | 20px |

Line designations are not shown (`show-line = false`).  All rows are
uniform size; position in the list communicates priority.

---

## Whitespace and visual hierarchy rules

1. No visible dividing lines within the left rail.  Vertical whitespace between
   DATE, CLOCK, WASTE, and MASCOT is sufficient.
2. One horizontal separator line at `y=182` (stroke ≈ 1–2 px, `#444`) marks the
   boundary between WEATHER and the lower information zone.  One vertical separator
   line at `x=534` (stroke 1 px, `#444`, y=334–476) divides TRANSPORT from TRELLO.
   These are the only structural lines on the canvas.
3. Priority is communicated by size and position, not labels or borders.
   The WEATHER block and the NEXT departure are the two largest type elements;
   everything else is smaller.
4. No debug-style full timestamps appear on the canvas in normal operation.
   The CLOCK `ca. HH:MM` label communicates freshness; no `last_update` slot exists.
5. The calendar block is rendered as one image slot so the renderer can rebalance
   visible events across a configurable number of displayed days while keeping
   overflow indicators aligned inside the block.
6. The MASCOT is intentionally small and low (bottom-left corner) so it reads as a
   personality accent, not a focal element.

---

## Relationship to other records

| Record  | Relationship |
|---------|-------------|
| DD-009  | Introduced the two-zone grid and the rationale for removing the old free-positioned layout.  This record supersedes DD-009's typography and state notes and adds the complete reference tables. |
| DD-007  | Defines `TextSpan`, `RichLine`, `StyledLine`, and `data-bbox-*` auto-sizing — the mechanisms used to implement the delayed and cancelled states above. |
| DD-008  | Defines the MVG FIB v2 departure source that populates TRANSPORT. |
| (Trello source) | The `trello_cards` source and `trello_cards_text` renderer populate TRELLO.  Credentials (`api_key`, `token`) are supplied via `secrets.toml` placeholders. |
| ADR-0003 | SVG template as the layout format; the region IDs above are the SVG element `id` values used by that contract. |
