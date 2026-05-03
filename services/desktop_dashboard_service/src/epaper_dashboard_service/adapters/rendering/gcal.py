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
        day_count = int(cfg.get("day-count", data.display_days if data.display_days is not None else _DEFAULT_DISPLAY_DAYS))
        font_size = int(cfg.get("font-size", 14))
        header_font_size = int(cfg.get("header-font-size", font_size + 2))
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
        font = _load_font(font_path, font_size)
        header_font = _load_font(bold_font_path, header_font_size)

        _draw_sections(draw, width, height, sections, font=font, header_font=header_font, column_gap=column_gap)
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


def _draw_sections(
    draw: ImageDraw.ImageDraw,
    width: int,
    height: int,
    sections: tuple[CalendarDaySection, ...],
    *,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    header_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    column_gap: int,
) -> None:
    if not sections:
        return

    column_count = len(sections)
    inner_gap = column_gap * max(column_count - 1, 0)
    column_width = max(40, (width - inner_gap) // column_count)
    header_height = _line_height(draw, header_font)
    line_height = _line_height(draw, font)
    header_y = 0
    line_y = header_height + 8

    for index, section in enumerate(sections):
        x = index * (column_width + column_gap)
        draw.text((x, header_y), _truncate_text(draw, section.label, column_width, header_font), fill=0, font=header_font)
        y = line_y

        lines = [_format_event(event) for event in section.visible_events]
        if section.hidden_count > 0:
            if lines:
                lines[-1] = _append_overflow_marker(lines[-1])
            else:
                lines = ["..."]
        elif not lines:
            lines = ["No events"]

        available_height = max(height - y, line_height)
        max_lines = max(1, available_height // line_height)
        for line in lines[:max_lines]:
            draw.text((x, y), _truncate_text(draw, line, column_width, font), fill=0, font=font)
            y += line_height


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
    truncated = text
    while truncated and draw.textlength(f"{truncated}{ellipsis}", font=font) > max_width:
        truncated = truncated[:-1]
    return f"{truncated.rstrip()}{ellipsis}" if truncated else ellipsis


def _append_overflow_marker(line: str) -> str:
    """Append the overflow marker to the truncated entry itself.

    This keeps the dots visually attached to the last visible event, matching the
    requested "show there are more events than displayed" behavior inside a fixed
    calendar column.  Empty overflowing days still render standalone ``...``.
    """
    return f"{line} ..."
