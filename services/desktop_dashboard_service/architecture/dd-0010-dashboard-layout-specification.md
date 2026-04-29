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
│  DATE           │  WEATHER                                                       │
│  (8,0,168,68)   │  (188,6,606,200)                                              │
│                 │                                                                 │
│  CLOCK          │ ─── SEPARATOR (y=212, x=192–794) ───────────────────────────  │
│  (51,100,76,96) │                                                                 │
│                 │  [TRAIN_ICON 192,214]  TRANSPORT (232,228,556,242)            │
│                 │                                                                 │
│  MASCOT         │                                                                 │
│  (10,350,130,130)│                                                               │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Region table

Each row is `(x, y, width, height)` — origin at top-left corner of the region's content
box, not the glyph baseline.

| Region ID       | Slot / element     | x   | y   | w   | h   | Priority   |
|-----------------|--------------------|-----|-----|-----|-----|------------|
| `DATE`          | `calendar` text    |   8 |   0 | 168 |  68 | secondary  |
| `CLOCK`         | `analog_clock` img |   7 | 110 | 168 | 190 | tertiary   |
| `MASCOT`        | `image_pool` img   |  10 | 350 | 130 | 130 | tertiary   |
| `WEATHER`       | `weather_block` img| 188 |   6 | 606 | 200 | primary    |
| `SEPARATOR`     | `<line>` element   | 192 | 212 | 602 |   1 | structural |
| `TRAIN_ICON`    | `<path>` element   | 192 | 214 |  35 |  46 | structural |
| `TRANSPORT`     | `trains` text      | 248 | 248 | 540 | 222 | primary    |

Notes:
- The DATE text baseline is `y=32`; the region box starts at `y=0` to include ascenders.
- CLOCK is `size_px=154` = 85 % of the 182 px rail.  The PIL canvas is wider than
  the face (~168 px) to fit the `ca. HH:MM` label; `x=7` centers it in the rail.
  `show_face=false` hides the outer ring; only hands and the validity indicator remain.
- TRANSPORT bottom edge: `y=470`, leaving a 10 px margin from the canvas bottom.
- TRANSPORT starts at `y=248`, giving a 36 px gap from the separator at `y=212`.
- TRANSPORT text starts at `x=248`, which clears the train icon right edge (~235 px).
- The gutter between RAIL and MAIN is 5 px (x=183–187); it is intentionally empty.
- No visible dividers separate regions within the rail; whitespace alone defines zones.

### Transport column layout (within TRANSPORT slot)

The timetable uses three implicit fixed-width columns.  All coordinates are
absolute (canvas-relative).

| Column       | Left edge (x) | Nominal width | Right edge (x) |
|--------------|--------------|---------------|----------------|
| Departure time | 248        | 88 px         | 336            |
| Destination  | 348          | 440 px        | 788            |

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
| Transport — station name          | TRANSPORT     | 26        | 700    | normal  |
| Transport — time                  | TRANSPORT     | 20        | 400    | normal  |
| Transport — destination           | TRANSPORT     | 20        | 400    | normal  |

Sizing rule: the TRANSPORT slot declares `data-bbox-width="540"` and
`data-bbox-height="238"`.  The auto-fit heuristic sizes the overall block first;
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
   DATE, CLOCK, and MASCOT is sufficient.
2. One separator line at `y=212` (stroke ≈ 1–2 px, `#444`) marks the boundary
   between WEATHER and TRANSPORT.  It is the only structural line on the canvas.
3. Priority is communicated by size and position, not labels or borders.
   The WEATHER block and the NEXT departure are the two largest type elements;
   everything else is smaller.
4. No debug-style full timestamps appear on the canvas in normal operation.
   The CLOCK `ca. HH:MM` label communicates freshness; no `last_update` slot exists.
5. The MASCOT is intentionally small and low (bottom-left corner) so it reads as a
   personality accent, not a focal element.

---

## Relationship to other records

| Record  | Relationship |
|---------|-------------|
| DD-009  | Introduced the two-zone grid and the rationale for removing the old free-positioned layout.  This record supersedes DD-009's typography and state notes and adds the complete reference tables. |
| DD-007  | Defines `TextSpan`, `RichLine`, `StyledLine`, and `data-bbox-*` auto-sizing — the mechanisms used to implement the delayed and cancelled states above. |
| DD-008  | Defines the MVG FIB v2 departure source that populates TRANSPORT. |
| ADR-0003 | SVG template as the layout format; the region IDs above are the SVG element `id` values used by that contract. |
