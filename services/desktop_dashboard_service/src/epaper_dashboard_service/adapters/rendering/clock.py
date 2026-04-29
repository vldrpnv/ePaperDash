"""Analog validity-window clock renderer.

Produces a self-contained PIL image showing:
- outer clock circle
- optional hour hand (no minute or second hand)
- optional 12-position tick marks (one per 5-minute mark)
- a validity-window indicator (sector arc or end hand)
- optional text label showing the validity range

The rendered image is suitable for black/white e-paper output.

Configuration keys in ``renderer_config`` (all optional):
- ``size_px``                  int, default 80  — diameter of the clock face
- ``validity_window_minutes``  int, default 5   — width of the validity window
- ``window_start_mode``        str, default ``"start_at_next_minute"``
                               ``"start_at_render_time"`` | ``"start_at_next_minute"``
- ``label_mode``               str, default ``"range"``
                               ``"none"`` | ``"range"`` | ``"approx"``
- ``sector_style``             str, default ``"outer_arc"``
                               ``"outer_arc"`` — thick arc along the rim spanning the window
                               ``"end_hand"``  — single long hand pointing to the window end
- ``show_hour_hand``           bool, default True
- ``show_face``                bool, default True  — draw the outer circle ring;
                               set to False to show only hands and indicators
- ``show_tick_marks``          bool, default True
- ``x``                        int, default 0   — placement x on the dashboard
- ``y``                        int, default 0   — placement y on the dashboard
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from epaper_dashboard_service.domain.models import ClockData, ImagePlacement, PanelDefinition
from epaper_dashboard_service.domain.ports import RendererPlugin

# ---------------------------------------------------------------------------
# Paths to bundled fonts (same directory structure as weather renderer)
# ---------------------------------------------------------------------------
_FONTS_DIR = Path(__file__).parent.parent / "fonts"
_DEFAULT_FONT = _FONTS_DIR / "DejaVuSans.ttf"


# ---------------------------------------------------------------------------
# Window computation
# ---------------------------------------------------------------------------

def _compute_window(
    render_time: datetime,
    validity_window_minutes: int,
    window_start_mode: str,
) -> tuple[datetime, datetime]:
    """Return *(window_start, window_end)* for the given render time and mode.

    ``start_at_next_minute``:
      - If render time has any sub-minute component (seconds or microseconds),
        round up to the next whole minute.
      - If render time is already exactly on a whole minute, use it as-is.

    ``start_at_render_time``:
      - Use the exact render time as the window start.
    """
    if window_start_mode == "start_at_next_minute":
        if render_time.second > 0 or render_time.microsecond > 0:
            start = render_time.replace(second=0, microsecond=0) + timedelta(minutes=1)
        else:
            start = render_time.replace(second=0, microsecond=0)
    else:
        # start_at_render_time
        start = render_time
    end = start + timedelta(minutes=validity_window_minutes)
    return start, end


# ---------------------------------------------------------------------------
# Angle helpers
# ---------------------------------------------------------------------------

def _minute_fraction_to_pil_angle(minute_fraction: float) -> float:
    """Convert a fractional minute position (0–60) to a PIL arc angle.

    PIL angle convention: 0° = 3 o'clock, increasing clockwise.
    12 o'clock is at -90° (= 270°).
    """
    return (minute_fraction / 60.0 * 360.0 - 90.0) % 360.0


def _hour_hand_pil_angle(dt: datetime) -> float:
    """Return the PIL angle for the hour hand at the given datetime."""
    # Hour hand completes one full rotation per 12 hours.
    # Total degrees from 12 o'clock = hours_in_12h * 30 + minutes * 0.5
    hours_in_12 = dt.hour % 12
    degrees_from_12 = hours_in_12 * 30.0 + dt.minute * 0.5
    return (degrees_from_12 - 90.0) % 360.0


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------

def _draw_clock(
    render_time: datetime,
    size_px: int,
    validity_window_minutes: int,
    window_start_mode: str,
    label_mode: str,
    show_hour_hand: bool,
    show_tick_marks: bool,
    sector_style: str = "outer_arc",
    show_face: bool = True,
) -> Image.Image:
    """Render the analog clock face and return a grayscale PIL Image.

    The image width is at least ``size_px`` wide, expanded when the text label
    requires more horizontal space.  The image height equals ``size_px`` when
    ``label_mode`` is ``"none"``, and ``size_px + label_height`` otherwise,
    where *label_height* is derived proportionally from ``size_px``.

    ``sector_style`` controls how the validity window is visualised:
    - ``"outer_arc"``: a thick arc drawn along the clock rim spanning the window.
    - ``"end_hand"``: a single long hand pointing to the end of the validity window.
    """
    font_size = max(10, size_px // 5)
    label_height = 0 if label_mode == "none" else font_size + 6

    # Compute validity window first so we can measure the label width.
    window_start, window_end = _compute_window(
        render_time, validity_window_minutes, window_start_mode
    )

    # Build label text (used both for measurement and drawing).
    if label_mode == "range":
        label_text: str | None = (
            f"{window_start.strftime('%H:%M')}\u2013{window_end.strftime('%H:%M')}"
        )
    elif label_mode == "approx":
        label_text = f"ca. {window_start.strftime('%H:%M')}"
    else:
        label_text = None

    # Load font early so we can measure label width.
    if label_text is not None:
        try:
            font: ImageFont.FreeTypeFont | ImageFont.ImageFont = ImageFont.truetype(
                str(_DEFAULT_FONT), font_size
            )
        except Exception:
            font = ImageFont.load_default()

        # Measure label on a temporary draw surface.
        _tmp = ImageDraw.Draw(Image.new("L", (1, 1)))
        try:
            bbox = _tmp.textbbox((0, 0), label_text, font=font)
            label_w = bbox[2] - bbox[0]
        except AttributeError:
            label_w = len(label_text) * font_size // 2
    else:
        label_w = 0
        font = ImageFont.load_default()  # not used but satisfies type checker

    # Canvas is wide enough for both the clock face and the label.
    canvas_w = max(size_px, label_w + 4)
    total_height = size_px + label_height

    canvas = Image.new("L", (canvas_w, total_height), 255)
    draw = ImageDraw.Draw(canvas)

    cx = canvas_w // 2
    cy = size_px // 2
    radius = size_px // 2 - 2  # just inside the image edge

    # 1. Outer circle
    if show_face:
        draw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            outline=0,
            width=max(1, size_px // 40),
        )

    # 2. Tick marks — 12 positions, one per 5-minute interval
    if show_tick_marks:
        tick_len = max(3, size_px // 14)
        tick_width = max(1, size_px // 40)
        for i in range(12):
            angle_rad = math.radians(i * 30 - 90)
            outer = radius - 1
            inner = outer - tick_len
            x0 = cx + outer * math.cos(angle_rad)
            y0 = cy + outer * math.sin(angle_rad)
            x1 = cx + inner * math.cos(angle_rad)
            y1 = cy + inner * math.sin(angle_rad)
            draw.line([(x0, y0), (x1, y1)], fill=0, width=tick_width)

    # 3. Draw validity-window indicator
    start_min = window_start.minute + window_start.second / 60.0
    end_min = window_end.minute + window_end.second / 60.0
    start_angle = _minute_fraction_to_pil_angle(start_min)
    end_angle = _minute_fraction_to_pil_angle(end_min)

    if sector_style == "end_hand":
        # A single long hand pointing to the window end — like a minute hand
        # but reaching close to the clock rim to clearly indicate the end position.
        end_angle_rad = math.radians(end_angle)
        end_hand_length = radius * 0.88
        end_hand_width = max(2, size_px // 25)
        ex = cx + end_hand_length * math.cos(end_angle_rad)
        ey = cy + end_hand_length * math.sin(end_angle_rad)
        draw.line([(cx, cy), (ex, ey)], fill=0, width=end_hand_width)
    else:
        # outer_arc (default): thick arc along the rim spanning the full window
        arc_thickness = max(4, size_px // 8)
        arc_radius = radius - arc_thickness // 2 - 1
        arc_bbox = [
            cx - arc_radius,
            cy - arc_radius,
            cx + arc_radius,
            cy + arc_radius,
        ]
        # Ensure the arc is drawn clockwise from start to end.
        if end_angle <= start_angle:
            end_angle += 360.0
        draw.arc(arc_bbox, start=start_angle, end=end_angle, fill=0, width=arc_thickness)

    # 4. Hour hand
    if show_hour_hand:
        hand_angle_rad = math.radians(_hour_hand_pil_angle(render_time))
        hand_length = radius * 0.55
        hand_width = max(2, size_px // 20)
        hx = cx + hand_length * math.cos(hand_angle_rad)
        hy = cy + hand_length * math.sin(hand_angle_rad)
        draw.line([(cx, cy), (hx, hy)], fill=0, width=hand_width)

    # Center dot
    dot_r = max(2, size_px // 22)
    draw.ellipse(
        [cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r],
        fill=0,
    )

    # 5. Label
    if label_text is not None and label_height > 0:
        text_x = max(0, (canvas_w - label_w) // 2)
        text_y = size_px + 2
        draw.text((text_x, text_y), label_text, fill=0, font=font)

    return canvas


# ---------------------------------------------------------------------------
# Renderer plugin
# ---------------------------------------------------------------------------

class AnalogClockRenderer(RendererPlugin):
    """Renders an analog validity-window clock as a self-contained PIL image.

    Returns a single ``ImagePlacement`` whose position is read from
    ``renderer_config`` keys ``x`` and ``y`` (both default to 0), or from
    the SVG ``<image>`` slot geometry injected by the application service.
    """

    name = "analog_clock"
    supported_type = ClockData

    def render(self, data: ClockData, panel: PanelDefinition) -> tuple[ImagePlacement, ...]:
        cfg = panel.renderer_config
        size_px = int(cfg.get("size_px", 80))
        validity_window_minutes = int(cfg.get("validity_window_minutes", 5))
        window_start_mode = str(cfg.get("window_start_mode", "start_at_next_minute"))
        label_mode = str(cfg.get("label_mode", "range"))
        sector_style = str(cfg.get("sector_style", "outer_arc"))
        show_hour_hand = _parse_bool(cfg.get("show_hour_hand", True))
        show_tick_marks = _parse_bool(cfg.get("show_tick_marks", True))
        show_face = _parse_bool(cfg.get("show_face", True))
        x = int(cfg.get("x", 0))
        y = int(cfg.get("y", 0))

        image = _draw_clock(
            render_time=data.render_time,
            size_px=size_px,
            validity_window_minutes=validity_window_minutes,
            window_start_mode=window_start_mode,
            label_mode=label_mode,
            show_hour_hand=show_hour_hand,
            show_tick_marks=show_tick_marks,
            sector_style=sector_style,
            show_face=show_face,
        )

        return (ImagePlacement(image=image, x=x, y=y),)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_bool(value: object) -> bool:
    """Coerce a config value to bool, accepting strings like 'false'/'true'."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() not in ("false", "0", "no", "off")
    return bool(value)
