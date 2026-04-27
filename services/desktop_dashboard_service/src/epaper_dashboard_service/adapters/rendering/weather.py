"""Weather block renderer — produces a self-contained PIL image for the weather_block slot.

The renderer draws three rows onto an 800×170 grayscale canvas:

Row 1 (y 0–30):   Today overview — condition label, temp min/max, precip if notable.
Row 2 (y 32–145): Three smart 4-hour blocks with icon + time label + temp range.
Row 3 (y 148–168): Tomorrow overview — small icon + condition + temp range.

The canvas size is derived from the `width` and `height` values injected into
`panel.renderer_config` by the application service from the SVG image-slot geometry.
The renderer returns a single ``ImagePlacement`` that composites over the dashboard.

Icon rendering is delegated to a ``WeatherIconProvider``.  When the provider returns
``None`` (e.g. ``NullWeatherIconProvider`` or a missing file), the condition Unicode
character is drawn as text instead — ensuring the block always renders something useful.

Font rendering uses bundled DejaVu Sans TTF files so there is no system font dependency.
A ``font_path`` override in ``renderer_config`` (as an absolute path string) replaces
the bundled default.
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

from epaper_dashboard_service.domain.i18n import ENGLISH, Translations
from epaper_dashboard_service.domain.models import (
    DashboardTextBlock,
    ImagePlacement,
    PanelDefinition,
    WeatherForecast,
    WeatherPeriod,
)
from epaper_dashboard_service.domain.ports import RendererPlugin, WeatherIconProvider

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Paths to bundled fonts
# ---------------------------------------------------------------------------
_FONTS_DIR = Path(__file__).parent.parent / "fonts"
_DEFAULT_FONT = _FONTS_DIR / "DejaVuSans.ttf"
_BOLD_FONT = _FONTS_DIR / "DejaVuSans-Bold.ttf"


# ---------------------------------------------------------------------------
# Layout helpers — all positions are derived from the canvas height at render
# time so the block adapts to whatever size the SVG slot declares.
# ---------------------------------------------------------------------------

def _compute_layout(height: int, base_font_size: int | None = None) -> dict[str, int]:
    """Return a dict of layout metrics computed proportionally from *height*.

    When *base_font_size* is provided it is used directly as ``font_lg_size``
    and all other font sizes are scaled from it, allowing the caller to pin
    the overall text scale independently of the slot height.
    """
    row1_h = max(22, height * 9 // 100)
    row1_y = 6
    sep1_y = row1_y + row1_h + 4
    row2_top = sep1_y + 4
    row3_h = max(28, height * 10 // 100)
    row3_y = height - row3_h
    sep2_y = row3_y - 6
    row2_bottom = sep2_y - 4
    row2_h = row2_bottom - row2_top
    icon_size = min(120, max(40, row2_h * 55 // 100))
    small_icon_size = max(24, row3_h - 8)
    if base_font_size is not None:
        font_lg_size = base_font_size
        font_md_size = max(10, int(base_font_size * 0.75))
        font_row3_size = max(10, int(base_font_size * 0.80))
        font_sm_size = max(9, int(base_font_size * 0.60))
    else:
        # Font sizes: scale with height, capped to stay readable.
        scale_100 = min(130, height * 100 // 170)  # integer %-of-default scale
        font_lg_size = max(14, min(28, 20 * scale_100 // 100))
        font_md_size = max(12, min(22, 16 * scale_100 // 100))
        font_row3_size = max(11, min(22, 17 * scale_100 // 100))  # larger than font_sm
        font_sm_size = max(10, min(17, 13 * scale_100 // 100))
    return {
        "row1_y": row1_y,
        "sep1_y": sep1_y,
        "row2_top": row2_top,
        "row2_bottom": row2_bottom,
        "sep2_y": sep2_y,
        "row3_y": row3_y,
        "icon_size": icon_size,
        "small_icon_size": small_icon_size,
        "font_lg_size": font_lg_size,
        "font_md_size": font_md_size,
        "font_row3_size": font_row3_size,
        "font_sm_size": font_sm_size,
    }


# ---------------------------------------------------------------------------
# Public renderer
# ---------------------------------------------------------------------------

class WeatherBlockRenderer(RendererPlugin):
    """Render a ``WeatherForecast`` as a composited PIL image block.

    Args:
        icon_provider: Provider that returns grayscale PIL images for condition icons.
        font_path: Override path to a TTF font file; if ``None`` the bundled
            DejaVu Sans is used.
        bold_font_path: Override path to a bold TTF; falls back to the regular font.
    """

    name = "weather_block"
    supported_type = WeatherForecast

    def __init__(
        self,
        icon_provider: WeatherIconProvider,
        font_path: Path | None = None,
        bold_font_path: Path | None = None,
        translations: Translations | None = None,
    ) -> None:
        self._icon_provider = icon_provider
        self._font_path = font_path or _DEFAULT_FONT
        self._bold_font_path = bold_font_path or _BOLD_FONT
        self._translations = translations or ENGLISH

    def render(
        self, data: WeatherForecast, panel: PanelDefinition
    ) -> tuple[DashboardTextBlock | ImagePlacement, ...]:
        x = int(panel.renderer_config.get("x", 0))
        y = int(panel.renderer_config.get("y", 190))
        width = int(panel.renderer_config.get("width", 800))
        height = int(panel.renderer_config.get("height", 170))

        # Allow font path overrides from renderer_config
        font_path_str = panel.renderer_config.get("font_path")
        font_path = Path(font_path_str) if font_path_str else self._font_path
        bold_font_path_str = panel.renderer_config.get("bold_font_path")
        bold_font_path = Path(bold_font_path_str) if bold_font_path_str else self._bold_font_path

        base_font_size_raw = panel.renderer_config.get("base_font_size")
        base_font_size: int | None = int(base_font_size_raw) if base_font_size_raw is not None else None

        icon_size_factor_raw = panel.renderer_config.get("icon_size_factor")
        icon_size_factor: float = float(icon_size_factor_raw) if icon_size_factor_raw is not None else 1.0

        tomorrow_icon_size_factor_raw = panel.renderer_config.get("tomorrow_icon_size_factor")
        tomorrow_icon_size_factor: float = float(tomorrow_icon_size_factor_raw) if tomorrow_icon_size_factor_raw is not None else 1.0

        precip_prob_threshold_raw = panel.renderer_config.get("precip_prob_threshold")
        precip_prob_threshold: int = int(precip_prob_threshold_raw) if precip_prob_threshold_raw is not None else 40

        precip_mm_threshold_raw = panel.renderer_config.get("precip_mm_threshold")
        precip_mm_threshold: float = float(precip_mm_threshold_raw) if precip_mm_threshold_raw is not None else 0.1

        now = datetime.now().astimezone()
        canvas = Image.new("L", (width, height), color=255)  # white background
        draw = ImageDraw.Draw(canvas)

        _draw_weather_block(
            draw, canvas, data, now, width, height, self._icon_provider,
            font_path, bold_font_path, base_font_size,
            icon_size_factor, tomorrow_icon_size_factor,
            precip_prob_threshold, precip_mm_threshold,
            self._translations,
        )

        return (ImagePlacement(image=canvas, x=x, y=y),)


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def _load_font(path: Path, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(str(path), size)
    except (OSError, AttributeError):
        return ImageFont.load_default()


def _draw_weather_block(
    draw: ImageDraw.ImageDraw,
    canvas: Image.Image,
    data: WeatherForecast,
    now: datetime,
    width: int,
    height: int,
    icon_provider: WeatherIconProvider,
    font_path: Path,
    bold_font_path: Path,
    base_font_size: int | None = None,
    icon_size_factor: float = 1.0,
    tomorrow_icon_size_factor: float = 1.0,
    precip_prob_threshold: int = 40,
    precip_mm_threshold: float = 0.1,
    translations: Translations | None = None,
) -> None:
    tr = translations or ENGLISH
    lo = _compute_layout(height, base_font_size)
    icon_size = max(16, int(lo["icon_size"] * icon_size_factor))
    small_icon_size = max(16, int(lo["small_icon_size"] * tomorrow_icon_size_factor))
    font_lg = _load_font(bold_font_path, lo["font_lg_size"])
    font_md = _load_font(font_path, lo["font_md_size"])
    font_row3 = _load_font(font_path, lo["font_row3_size"])
    font_sm = _load_font(font_path, lo["font_sm_size"])

    today = now.date()
    tomorrow = today + timedelta(days=1)

    today_periods = [p for p in data.periods if p.start_time.astimezone().date() == today]
    tomorrow_periods = [p for p in data.periods if p.start_time.astimezone().date() == tomorrow]

    # -----------------------------------------------------------------------
    # Row 1: today overview
    # -----------------------------------------------------------------------
    if today_periods:
        _draw_row1(draw, today_periods, lo["row1_y"], width, font_lg,
                   precip_prob_threshold, precip_mm_threshold, tr)

    # -----------------------------------------------------------------------
    # Separator line between row 1 and row 2
    # -----------------------------------------------------------------------
    draw.line([(8, lo["sep1_y"]), (width - 8, lo["sep1_y"])], fill=180, width=1)

    # -----------------------------------------------------------------------
    # Row 2: three smart 4-hour blocks
    # -----------------------------------------------------------------------
    blocks = _select_weather_blocks(data.periods, now, tr)
    col_width = width // 3
    for col_idx, block in enumerate(blocks[:3]):
        block_x = col_idx * col_width
        _draw_block_column(
            draw, canvas, block, block_x, col_width,
            lo["row2_top"], lo["row2_bottom"], icon_size,
            icon_provider, font_md, font_sm,
            precip_prob_threshold, precip_mm_threshold,
        )

    # -----------------------------------------------------------------------
    # Separator line between row 2 and row 3
    # -----------------------------------------------------------------------
    draw.line([(8, lo["sep2_y"]), (width - 8, lo["sep2_y"])], fill=180, width=1)

    # -----------------------------------------------------------------------
    # Row 3: tomorrow overview
    # -----------------------------------------------------------------------
    if tomorrow_periods:
        _draw_row3(draw, canvas, tomorrow_periods, lo["row3_y"], width, height,
                   small_icon_size, icon_provider, font_row3, font_sm,
                   precip_prob_threshold, precip_mm_threshold, tr)


def _draw_row1(
    draw: ImageDraw.ImageDraw,
    periods: list[WeatherPeriod],
    y: int,
    width: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    precip_prob_threshold: int = 40,
    precip_mm_threshold: float = 0.1,
    translations: Translations | None = None,
) -> None:
    tr = translations or ENGLISH
    temps = [p.temperature_c for p in periods]
    t_min = min(temps)
    t_max = max(temps)
    condition = _dominant_condition(periods)
    total_mm = sum(p.precipitation_mm for p in periods)
    max_prob = max(p.precipitation_probability_percent for p in periods)

    text = f"{tr.condition(condition)}   {t_min:.0f}°\u2013{t_max:.0f}°C"
    if max_prob >= precip_prob_threshold or total_mm > precip_mm_threshold:
        text += f"   {total_mm:.1f}mm ({max_prob}%)"

    draw.text((12, y), text, font=font, fill=0)


def _draw_row3(
    draw: ImageDraw.ImageDraw,
    canvas: Image.Image,
    periods: list[WeatherPeriod],
    y: int,
    width: int,
    height: int,
    small_icon_size: int,
    icon_provider: WeatherIconProvider,
    font_md: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    font_sm: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    precip_prob_threshold: int = 40,
    precip_mm_threshold: float = 0.1,
    translations: Translations | None = None,
) -> None:
    tr = translations or ENGLISH
    temps = [p.temperature_c for p in periods]
    t_min = min(temps)
    t_max = max(temps)
    condition = _dominant_condition(periods)
    total_mm = sum(p.precipitation_mm for p in periods)
    max_prob = max(p.precipitation_probability_percent for p in periods)

    icon_char = _dominant_condition_icon(periods)
    icon_img = icon_provider.get_icon(icon_char, small_icon_size, small_icon_size)
    text_x = 10
    if icon_img is not None:
        # Paste with alpha derived from grayscale value (darker = more opaque)
        canvas.paste(icon_img, (10, y))
        text_x = 10 + small_icon_size + 6
    else:
        draw.text((10, y + (small_icon_size - 16) // 2), icon_char, font=font_md, fill=0)
        text_x = 10 + 22

    text = f"{tr.tomorrow}: {tr.condition(condition)}  {t_min:.0f}\u2013{t_max:.0f}\u00b0C"
    if max_prob >= precip_prob_threshold or total_mm > precip_mm_threshold:
        text += f"  {total_mm:.1f}mm ({max_prob}%)"
    row_text_y = y + (small_icon_size - 14) // 2
    draw.text((text_x, row_text_y), text, font=font_md, fill=0)


def _draw_block_column(
    draw: ImageDraw.ImageDraw,
    canvas: Image.Image,
    block: "_WeatherBlock",
    col_x: int,
    col_width: int,
    row_top: int,
    row_bottom: int,
    icon_size: int,
    icon_provider: WeatherIconProvider,
    font_md: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    font_sm: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    precip_prob_threshold: int = 40,
    precip_mm_threshold: float = 0.1,
) -> None:
    # --- icon ---
    icon_char = block.condition_icon
    icon_y = row_top + 2
    icon_x = col_x + (col_width - icon_size) // 2
    icon_img = icon_provider.get_icon(icon_char, icon_size, icon_size)
    if icon_img is not None:
        canvas.paste(icon_img, (icon_x, icon_y))
    else:
        # Fallback: draw the Unicode character at a readable size
        fallback_size = max(20, icon_size // 2)
        draw.text(
            (col_x + col_width // 2 - fallback_size // 2,
             icon_y + (icon_size - fallback_size) // 2),
            icon_char,
            font=_load_font(_DEFAULT_FONT, fallback_size),
            fill=0,
        )

    # Measure font heights via textbbox for correct spacing.
    try:
        md_h = draw.textbbox((0, 0), "Ag", font=font_md)[3]
        sm_h = draw.textbbox((0, 0), "Ag", font=font_sm)[3]
    except AttributeError:
        md_h = 16
        sm_h = 13

    # --- time label ---
    label = block.time_label
    label_y = icon_y + icon_size + 4
    _draw_centered_text(draw, label, col_x, col_width, label_y, font_md)

    # --- temp range ---
    temp_text = f"{block.temp_min:.0f}°\u2013{block.temp_max:.0f}°C"
    temp_y = label_y + md_h + 2
    _draw_centered_text(draw, temp_text, col_x, col_width, temp_y, font_sm)

    # --- precip (only if notable) ---
    if block.precipitation_prob >= precip_prob_threshold or block.precipitation_mm > precip_mm_threshold:
        precip_text = f"{block.precipitation_mm:.1f}mm"
        precip_y = temp_y + sm_h + 2
        _draw_centered_text(draw, precip_text, col_x, col_width, precip_y, font_sm)


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    col_x: int,
    col_width: int,
    y: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
    except AttributeError:
        text_w = len(text) * 8  # rough fallback
    x = col_x + (col_width - text_w) // 2
    draw.text((x, y), text, font=font, fill=0)


# ---------------------------------------------------------------------------
# Smart 4-hour block selection
# ---------------------------------------------------------------------------

class _WeatherBlock:
    """Aggregated weather data for a 4-hour display block."""

    __slots__ = (
        "time_label",
        "condition_icon",
        "condition_label",
        "temp_min",
        "temp_max",
        "precipitation_prob",
        "precipitation_mm",
    )

    def __init__(
        self,
        time_label: str,
        condition_icon: str,
        condition_label: str,
        temp_min: float,
        temp_max: float,
        precipitation_prob: int,
        precipitation_mm: float,
    ) -> None:
        self.time_label = time_label
        self.condition_icon = condition_icon
        self.condition_label = condition_label
        self.temp_min = temp_min
        self.temp_max = temp_max
        self.precipitation_prob = precipitation_prob
        self.precipitation_mm = precipitation_mm


def _select_weather_blocks(
    periods: tuple[WeatherPeriod, ...],
    now: datetime,
    translations: Translations | None = None,
) -> list[_WeatherBlock]:
    """Return three ``_WeatherBlock`` instances for display in row 2.

    Algorithm
    ---------
    Define ``remaining = 22 - current_hour`` (hours left in today's 06-22 window).

    **remaining ≥ 12**: Three 4-h blocks fit inside today.  Distribute the
    slack evenly as integer gaps between blocks so they spread across the rest
    of the day:
        slack = remaining - 12
        B1 starts at current_hour
        B2 starts at current_hour + 4 + ceil(slack/2)
        B3 starts at current_hour + 8 + slack  (= 22 - 4)

    User examples:
      06:00  remaining=16 slack=4  → 06-10, 12-16, 18-22
      08:00  remaining=14 slack=2  → 08-12, 13-17, 18-22

    **remaining < 12**: Pack three contiguous 4-hour blocks from current_hour,
    crossing midnight into tomorrow when needed.

    User examples:
      15:00  → 15-19, 19-23, 23-03
      20:00  → 20-00, 00-04, 04-08
    """
    tr = translations or ENGLISH
    local_now = now.astimezone()
    today = local_now.date()
    tomorrow = today + timedelta(days=1)
    current_hour = local_now.hour

    remaining = 22 - current_hour  # hours remaining in today's day window

    if remaining >= 12:
        # Three 4-h blocks fit today — distribute slack evenly between them.
        slack = remaining - 12          # hours available as gaps between 3 blocks
        gap1 = -(-slack // 2)           # ceil(slack/2)
        gap2 = slack // 2               # floor(slack/2)
        chosen: list[tuple[date, int]] = [
            (today, current_hour),
            (today, current_hour + 4 + gap1),
            (today, current_hour + 8 + gap1 + gap2),
        ]
    else:
        # Pack three contiguous 4-hour blocks starting at current_hour, crossing midnight
        # into tomorrow when needed.
        chosen = []
        for i in range(3):
            h = current_hour + i * 4
            if h < 24:
                chosen.append((today, h))
            else:
                chosen.append((tomorrow, h - 24))

    # Build a lookup: (date, hour) → list of periods that start in that hour
    period_lookup: dict[tuple[date, int], list[WeatherPeriod]] = {}
    for p in periods:
        local_start = p.start_time.astimezone()
        key = (local_start.date(), local_start.hour)
        period_lookup.setdefault(key, []).append(p)

    blocks: list[_WeatherBlock] = []
    for block_date, block_hour in chosen:
        # Aggregate all periods in [block_hour, block_hour+4)
        block_periods: list[WeatherPeriod] = []
        for offset in range(4):
            actual_hour = block_hour + offset
            actual_date = block_date
            if actual_hour >= 24:
                actual_date = block_date + timedelta(days=1)
                actual_hour -= 24
            block_periods.extend(period_lookup.get((actual_date, actual_hour), []))

        # Use modulo so 24 displays as 00 (e.g. 20–00, not 20–24).
        end_label = (block_hour + 4) % 24
        label = f"{block_hour:02d}\u2013{end_label:02d}"
        if block_date != today:
            label = f"{tr.tomorrow_short} {label}"

        if not block_periods:
            blocks.append(
                _WeatherBlock(
                    time_label=label,
                    condition_icon="\u2753",
                    condition_label="Unknown",
                    temp_min=0,
                    temp_max=0,
                    precipitation_prob=0,
                    precipitation_mm=0.0,
                )
            )
            continue

        temps = [p.temperature_c for p in block_periods]
        icon_char = _dominant_condition_icon_from_list(block_periods)
        icon_label = _dominant_condition_from_list(block_periods)
        blocks.append(
            _WeatherBlock(
                time_label=label,
                condition_icon=icon_char,
                condition_label=icon_label,
                temp_min=min(temps),
                temp_max=max(temps),
                precipitation_prob=max(p.precipitation_probability_percent for p in block_periods),
                precipitation_mm=sum(p.precipitation_mm for p in block_periods),
            )
        )

    return blocks


# ---------------------------------------------------------------------------
# Condition aggregation helpers
# ---------------------------------------------------------------------------

# Severity order for dominant-condition selection (higher = more severe)
_ICON_SEVERITY: dict[str, int] = {
    "\u26a1": 6,        # ⚡ Thunderstorm
    "\u2614": 5,        # ☔ Rain
    "\u2744": 5,        # ❄ Snow
    "\U0001f32b": 4,    # 🌫 Fog
    "\u2601": 3,        # ☁ Cloudy
    "\u26c5": 2,        # ⛅ Partly cloudy
    "\u2600": 1,        # ☀ Sunny
    "\u2753": 0,        # ❓ Unknown
}


def _dominant_condition_icon_from_list(periods: list[WeatherPeriod]) -> str:
    if not periods:
        return "\u2753"
    return max(periods, key=lambda p: _ICON_SEVERITY.get(p.condition_icon, 0)).condition_icon


def _dominant_condition_from_list(periods: list[WeatherPeriod]) -> str:
    if not periods:
        return "Unknown"
    return max(periods, key=lambda p: _ICON_SEVERITY.get(p.condition_icon, 0)).condition_label


def _dominant_condition_icon(periods: list[WeatherPeriod]) -> str:
    return _dominant_condition_icon_from_list(periods)


def _dominant_condition(periods: list[WeatherPeriod]) -> str:
    return _dominant_condition_from_list(periods)
