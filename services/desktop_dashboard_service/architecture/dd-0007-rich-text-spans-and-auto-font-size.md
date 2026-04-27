# DD-007: Rich-text spans and bounding-box auto-font-size in SVG layout

## Status

Accepted

## Context

The train departures panel needs to display line labels in **bold** and cancelled departure times with a ~~strikethrough~~.
The existing `DashboardTextBlock.lines` field only carried plain strings, which cannot express per-segment formatting.

Additionally, the number of departure entries on a panel is configurable by the operator.  Hard-coding a font size in the SVG template would result in text that either overflows or looks too small depending on the configured `limit`.  A mechanism to automatically size the font to the available space was needed.

## Decision

### Rich-text spans

A new `TextSpan` dataclass is added to the domain models:

```
TextSpan(text: str, bold: bool = False, strikethrough: bool = False)
```

`DashboardTextBlock.lines` is typed as `tuple[str | RichLine | StyledLine, ...]` where:

- `str` — plain text line, rendered as before.
- `RichLine = tuple[TextSpan, ...]` — inline-formatted line; each `TextSpan` is emitted as one `<tspan>` element carrying `font-weight="bold"` or `text-decoration="line-through"` as appropriate.
- `StyledLine(spans, font_size, dy)` — a `RichLine` with optional per-line SVG attribute overrides:
  - `font_size: int | None` — when set, the SVG renderer emits a `font-size` attribute on the outer `<tspan>` wrapper, overriding the parent `<text>` element font size for that line only.
  - `dy: str | None` — when set, replaces the default `1.2em` line-advance used by the SVG renderer, allowing custom spacing above a specific line.

This change is backward-compatible: all existing callers that pass plain strings are unaffected.

### Bounding-box auto-font-size

A `<text>` element in an SVG template may declare `data-bbox-width` and `data-bbox-height` attributes.  When both are present the SVG renderer computes a font size using a heuristic proportional approximation:

- `from_width = bbox_width / (longest_line_chars × 0.55)`
- `from_height = bbox_height / (num_lines × 1.35)`
- `font_size = clamp(min(from_width, from_height), 8, 200)`

The heuristic is calibrated for proportional sans-serif fonts.  It is intentionally conservative so that text stays within the box rather than overflowing.  Renderer-config `font-size` values override the auto-calculated size when provided.

## Consequences

- The existing plain-string path in the SVG renderer is unchanged; new functionality is additive.
- Operators can control per-panel text sizing either by specifying `font-size` in `renderer_config` or by declaring a bounding box in the SVG template.
- The heuristic may under-size text slightly for narrow characters or short line counts; it can be tuned by adjusting `_CHAR_WIDTH_RATIO` and `_LINE_HEIGHT_RATIO` in `svg.py`.
