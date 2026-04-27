# ADR-007: Switch SVG renderer from CairoSVG to rsvg-convert (librsvg)

## Status

Accepted

## Context

The dashboard uses `text-decoration: line-through` (strikethrough) to indicate
cancelled or delayed train departures.  CairoSVG (the previous renderer) does
not render the CSS `text-decoration` property at all — neither via the `style=`
attribute nor as a presentation attribute.

A workaround was in place: the `_inject_strikethrough_lines` post-processor
scanned the SVG for `text-decoration="line-through"` tspan elements, estimated
the span width using the heuristic character-width ratio (`_CHAR_WIDTH_RATIO =
0.55`), removed the attribute, and injected a plain SVG `<line>` element at the
computed position.

The injected lines did not fit correctly because proportional font rendering
means the actual rendered width of a text span rarely matches the heuristic
estimate.  The strike lines were visually misaligned with the text they were
meant to cross out.

## Decision

Replace CairoSVG with **rsvg-convert** (part of the `librsvg` package) as the
SVG-to-PNG rasteriser.  `rsvg-convert` is invoked as a subprocess, reading SVG
bytes from stdin and writing PNG bytes to stdout.

`rsvg-convert` renders `text-decoration: line-through` natively and
accurately, so:

- The `_inject_strikethrough_lines` post-processing function is removed.
- The `cairosvg` Python package is removed from the project dependencies.
- `librsvg2-bin` is required as a system package.

The rest of the SVG generation pipeline (XML assembly, font-size auto-sizing,
slot validation, slot bounding-box checks) is unchanged.

## Consequences

- Strikethrough decoration on cancelled/delayed departures is rendered correctly
  and at the right position without any heuristic estimation.
- The `CairoSVG` Python dependency is removed; `librsvg2-bin` must be available
  on the host (`sudo apt-get install -y librsvg2-bin` on Debian/Ubuntu).
- The `copilot-setup-steps.yml` file documents the required system dependency
  for the Copilot agent environment.
- The heuristic `_CHAR_WIDTH_RATIO` and `_LINE_HEIGHT_RATIO` constants are
  retained because they are still used by the auto-font-size and overflow-check
  helpers (`_fit_font_size`, `check_content_overflow`).
