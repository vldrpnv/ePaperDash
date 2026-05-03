"""Renderer for Google Calendar events."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Protocol

from PIL import Image, ImageDraw, ImageFont

from epaper_dashboard_service.domain.models import GoogleCalendarEvent, GoogleCalendarEvents, ImagePlacement, PanelDefinition
from epaper_dashboard_service.domain.ports import RendererPlugin

_ALL_DAY_BULLET = "•"
_DEFAULT_DISPLAY_DAYS = 3
_DEFAULT_SOFT_DAY_LIMIT = 5
_DEFAULT_TOTAL_CAPACITY = 16
_DEFAULT_COLUMN_GAP = 12
_WEEKDAY_ABBR = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")

# Bundled fonts live under ``adapters/fonts/`` alongside the weather/clock
# renderers.  If they are unavailable at runtime, ``_load_font`` falls back to
# Pillow's default bitmap font so the calendar still renders.
_FONTS_DIR = Path(__file__).parent.parent / "fonts"
_DEFAULT_FONT = _FONTS_DIR / "DejaVuSans.ttf"
_BOLD_FONT = _FONTS_DIR / "DejaVuSans-Bold.ttf"


@dataclass(frozen=True)
class CalendarDaySection:
    day: date
    label: str
    visible_events: tuple[GoogleCalendarEvent, ...]
    hidden_count: int


class EventAllocationStrategy(Protocol):
    def allocate(
        self,
        counts: tuple[int, ...],
        *,
        total_capacity: int,
        soft_day_limit: int,
    ) -> tuple[int, ...]:
        """Return visible-event counts per day."""


class ProportionalEventAllocationStrategy:
    """Default event-allocation strategy for the calendar block.

    Behavior:
    - if all events fit within the total capacity, show all of them;
    - if every displayed day overflows the soft day limit, keep a visually even
      five-per-day presentation;
    - otherwise, keep days with ``<= soft_day_limit`` intact and distribute the
      remaining capacity proportionally across the longer days.
    """

    def allocate(
        self,
        counts: tuple[int, ...],
        *,
        total_capacity: int,
        soft_day_limit: int,
    ) -> tuple[int, ...]:
        if not counts:
            return ()

        total_events = sum(counts)
        if total_events <= total_capacity:
            return counts

        positive_counts = [count for count in counts if count > 0]
        if positive_counts and all(count > soft_day_limit for count in positive_counts):
            capped = tuple(min(count, soft_day_limit) for count in counts)
            if sum(capped) <= total_capacity:
                return capped

        protected = [count if count <= soft_day_limit else 0 for count in counts]
        protected_total = sum(protected)
        if protected_total >= total_capacity:
            return _allocate_proportionally(counts, total_capacity)

        overflow_counts = tuple(
            count
            for count in counts
            if count > soft_day_limit
        )
        remaining_capacity = total_capacity - protected_total
        if sum(overflow_counts) <= remaining_capacity:
            return tuple(protected[index] or counts[index] for index in range(len(counts)))

        proportional_overflow = _allocate_proportionally(overflow_counts, remaining_capacity)

        allocation: list[int] = []
        overflow_index = 0
        for index, count in enumerate(counts):
            if count <= soft_day_limit:
                allocation.append(count)
            else:
                allocation.append(proportional_overflow[overflow_index])
                overflow_index += 1
        return tuple(allocation)


@dataclass(frozen=True)
class _EventDisplayRow:
    """A single rendered line in the flowing event list."""
    day: date
    day_first: bool   # first event of this day across the whole list
    event_text: str   # formatted event text, possibly with overflow marker


class GoogleCalendarTextRenderer(RendererPlugin):
    """Render Google Calendar events as a single rebalanced multi-column image."""

    name = "google_calendar_text"
    supported_type = GoogleCalendarEvents

    def __init__(
        self,
        *,
        allocation_strategy: EventAllocationStrategy | None = None,
        font_path: Path | None = None,
        bold_font_path: Path | None = None,
    ) -> None:
        self._allocation_strategy = allocation_strategy or ProportionalEventAllocationStrategy()
        self._font_path = font_path or _DEFAULT_FONT
        self._bold_font_path = bold_font_path or _BOLD_FONT

    def render(
        self, data: GoogleCalendarEvents, panel: PanelDefinition
    ) -> tuple[ImagePlacement, ...]:
        cfg = panel.renderer_config
        x = int(cfg.get("x", 0))
        y = int(cfg.get("y", 0))
        width = int(cfg.get("width", 600))
        height = int(cfg.get("height", 124))
        total_capacity = int(cfg.get("max-total-events", _DEFAULT_TOTAL_CAPACITY))
        soft_day_limit = int(cfg.get("soft-day-limit", _DEFAULT_SOFT_DAY_LIMIT))
        day_count = _resolve_day_count(data, cfg)
        font_size = int(cfg.get("font-size", 14))
        column_gap = int(cfg.get("column-gap", _DEFAULT_COLUMN_GAP))
        font_path = Path(str(cfg.get("font_path"))) if cfg.get("font_path") else self._font_path
        bold_font_path = Path(str(cfg.get("bold_font_path"))) if cfg.get("bold_font_path") else self._bold_font_path

        sections = _build_day_sections(
            data,
            day_count=day_count,
            total_capacity=total_capacity,
            soft_day_limit=soft_day_limit,
            allocation_strategy=self._allocation_strategy,
        )

        canvas = Image.new("L", (width, height), color=255)
        draw = ImageDraw.Draw(canvas)
        _draw_sections(
            draw, width, height, sections,
            font_path=font_path,
            bold_font_path=bold_font_path,
            max_font_size=font_size,
            column_gap=column_gap,
        )
        return (ImagePlacement(image=canvas, x=x, y=y),)


def _build_day_sections(
    data: GoogleCalendarEvents,
    *,
    day_count: int,
    total_capacity: int,
    soft_day_limit: int,
    allocation_strategy: EventAllocationStrategy,
) -> tuple[CalendarDaySection, ...]:
    grouped_events: list[tuple[GoogleCalendarEvent, ...]] = []
    for day_offset in range(day_count):
        event_day = data.reference_date + timedelta(days=day_offset)
        grouped_events.append(
            tuple(event for event in data.events if event.event_date == event_day)
        )

    visible_counts = allocation_strategy.allocate(
        tuple(len(events) for events in grouped_events),
        total_capacity=total_capacity,
        soft_day_limit=soft_day_limit,
    )

    sections: list[CalendarDaySection] = []
    for day_offset, day_events in enumerate(grouped_events):
        event_day = data.reference_date + timedelta(days=day_offset)
        visible_count = visible_counts[day_offset] if day_offset < len(visible_counts) else 0
        sections.append(
            CalendarDaySection(
                day=event_day,
                label=_format_day_label(event_day, day_offset),
                visible_events=day_events[:visible_count],
                hidden_count=max(len(day_events) - visible_count, 0),
            )
        )
    return tuple(sections)


def _sections_to_display_rows(sections: tuple[CalendarDaySection, ...]) -> list[_EventDisplayRow]:
    """Flatten day sections into a single chronological list of display rows.

    Rules:
    - Sections with no visible events and no hidden events are skipped.
    - ``day_first=True`` marks the first event of each calendar day.
    - When a section has hidden entries the last visible event's text receives
      an overflow marker (``…`` appended via ``_append_overflow_marker``).
    - When a section has hidden entries but zero visible events a standalone
      ``"..."`` row is emitted instead.
    """
    rows: list[_EventDisplayRow] = []
    for section in sections:
        n = len(section.visible_events)
        if n == 0 and section.hidden_count == 0:
            continue
        for i, event in enumerate(section.visible_events):
            text = _format_event(event)
            if i == n - 1 and section.hidden_count > 0:
                text = _append_overflow_marker(text)
            rows.append(_EventDisplayRow(day=section.day, day_first=(i == 0), event_text=text))
        if n == 0 and section.hidden_count > 0:
            rows.append(_EventDisplayRow(day=section.day, day_first=True, event_text="..."))
    return rows


def _day_boundary_split(rows: list["_EventDisplayRow"]) -> int:
    """Return the index at which to start the right column.

    Picks the day-boundary closest to the midpoint so no single day is
    split across columns.  Returns ``len(rows)`` when there is only one
    day (everything in the left column).
    """
    n = len(rows)
    boundaries = [i for i in range(1, n) if rows[i].day_first]
    if not boundaries:
        return n
    mid = n / 2
    return min(boundaries, key=lambda i: abs(i - mid))


def _draw_sections(
    draw: ImageDraw.ImageDraw,
    width: int,
    height: int,
    sections: tuple[CalendarDaySection, ...],
    *,
    font_path: Path,
    bold_font_path: Path,
    max_font_size: int,
    column_gap: int,
) -> None:
    """Render all events as a flowing two-column chronological list.

    Font size is auto-calculated so that all rows fit within *height*,
    capped at *max_font_size*.  Each row carries an abbreviated weekday
    label (bold) on the first event of a day or when starting a new column.
    """
    rows = _sections_to_display_rows(sections)
    if not rows:
        font = _load_font(font_path, max_font_size)
        draw.text((0, 0), "No events", fill=0, font=font)
        return

    n_cols = 2
    split = _day_boundary_split(rows)
    # Tallest column determines font size so all rows fit.
    tallest = max(split, len(rows) - split) if split < len(rows) else len(rows)
    auto_font_size = max(8, int(height / (tallest * 1.3)))
    actual_font_size = min(max_font_size, auto_font_size)
    font = _load_font(font_path, actual_font_size)
    bold_font = _load_font(bold_font_path, actual_font_size)
    line_h = _line_height(draw, font)

    # Reserve a fixed prefix width for the 2-char weekday label ("Mo ").
    day_prefix_w = int(draw.textlength("Mo ", font=bold_font)) + 2
    col_width = (width - column_gap * (n_cols - 1)) // n_cols
    event_width = max(40, col_width - day_prefix_w)

    for i, row in enumerate(rows):
        col = 0 if i < split else 1
        row_in_col = i if col == 0 else i - split
        col_x = col * (col_width + column_gap)
        y = row_in_col * line_h
        # Show day label only on the first event of each day.
        if row.day_first:
            draw.text(
                (col_x, y),
                _WEEKDAY_ABBR[row.day.weekday()],
                fill=0,
                font=bold_font,
            )
        draw.text(
            (col_x + day_prefix_w, y),
            _truncate_text(draw, row.event_text, event_width, font),
            fill=0,
            font=font,
        )


def _allocate_proportionally(counts: tuple[int, ...], total_capacity: int) -> tuple[int, ...]:
    if total_capacity <= 0 or not counts:
        return tuple(0 for _ in counts)

    total = sum(counts)
    if total <= total_capacity:
        return counts

    quotas = [count * total_capacity / total for count in counts]
    allocation = [min(count, int(quota)) for count, quota in zip(counts, quotas, strict=True)]
    remaining = total_capacity - sum(allocation)

    if remaining > 0:
        remainders = sorted(
            (
                (quota - int(quota), index)
                for index, (quota, count) in enumerate(zip(quotas, counts, strict=True))
                if allocation[index] < count
            ),
            reverse=True,
        )
        for _, index in remainders:
            if remaining <= 0:
                break
            allocation[index] += 1
            remaining -= 1
    return tuple(allocation)


def _resolve_day_count(data: GoogleCalendarEvents, cfg: dict[str, object]) -> int:
    configured_day_count = cfg.get("day-count")
    if configured_day_count is not None:
        return int(configured_day_count)
    return data.display_days


def _format_event(event: GoogleCalendarEvent) -> str:
    if event.all_day or event.start_time is None:
        return f"{_ALL_DAY_BULLET} {event.title}"
    return f"{event.start_time.strftime('%H:%M')} {event.title}"


def _format_day_label(event_day: date, day_offset: int) -> str:
    suffix = ""
    if day_offset == 0:
        suffix = ", today"
    elif day_offset == 1:
        suffix = ", tomorrow"
    return f"{event_day.strftime('%A')}{suffix}"


def _load_font(path: Path, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(str(path), size)
    except (OSError, AttributeError):
        return ImageFont.load_default()


def _line_height(
    draw: ImageDraw.ImageDraw,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> int:
    bbox = draw.textbbox((0, 0), "Ag", font=font)
    return max((bbox[3] - bbox[1]) + 4, 12)


def _truncate_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> str:
    if draw.textlength(text, font=font) <= max_width:
        return text

    ellipsis = "..."
    low = 0
    high = len(text)
    best = ""
    while low <= high:
        mid = (low + high) // 2
        candidate = f"{text[:mid].rstrip()}{ellipsis}" if mid > 0 else ellipsis
        if draw.textlength(candidate, font=font) <= max_width:
            best = candidate
            low = mid + 1
        else:
            high = mid - 1
    return best or ellipsis


def _append_overflow_marker(line: str) -> str:
    """Append the overflow marker to the truncated entry itself.

    This keeps the dots visually attached to the last visible event, matching the
    requested "show there are more events than displayed" behavior inside a fixed
    calendar column.  Empty overflowing days still render standalone ``...``.
    """
    return f"{line} ..."
