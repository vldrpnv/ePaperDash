"""Content-pressure score calculation and display mode selection.

The dashboard operates in one of three display modes — calm, normal, or
overloaded — determined by a numeric content-pressure score computed before
rendering.  Higher scores indicate more information competing for space, which
triggers progressive reduction of decorative and low-priority elements.

Score weights
-------------
Each contributing factor adds a fixed number of points.  The factors and their
weights are defined in :data:`SCORE_WEIGHTS`.

Mode thresholds
---------------
- ``calm``      score ≤ 5
- ``normal``    6 ≤ score ≤ 12
- ``overloaded``  score ≥ 13

See ``dd-0013-content-pressure-modes.md`` for the design rationale.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DisplayMode(Enum):
    """Dashboard display mode selected by content-pressure score."""

    CALM = "calm"
    NORMAL = "normal"
    OVERLOADED = "overloaded"


# Score weights for each contributing factor.
SCORE_WEIGHTS: dict[str, int] = {
    "calendar_item_today_or_tomorrow": 2,
    "calendar_item_later_week": 1,
    "trello_card": 1,
    "weather_warning": 4,
    "rain_or_storm_tomorrow": 3,
    "waste_within_48h": 2,
    "train_disruption_or_delay": 4,
    "train_departure_count_above_5": 1,
}

# Mode boundary constants.
CALM_MAX_SCORE: int = 5
OVERLOADED_MIN_SCORE: int = 13


@dataclass(frozen=True)
class ContentPressureInputs:
    """Inputs used to compute the content-pressure score for one dashboard cycle.

    All counts are capped at the number that could realistically appear on the
    display; boolean flags represent the presence of an alert condition.
    """

    calendar_items_today_or_tomorrow: int = 0
    """Number of calendar events due today or tomorrow."""

    calendar_items_later_week: int = 0
    """Number of calendar events due later in the week (beyond tomorrow)."""

    trello_cards: int = 0
    """Number of Trello/task cards visible on the board."""

    weather_warning_present: bool = False
    """True when the forecast contains a severe-weather warning."""

    rain_or_storm_tomorrow: bool = False
    """True when tomorrow's forecast shows rain or storm conditions."""

    waste_within_48h: bool = False
    """True when a waste collection is due within the next 48 hours."""

    train_disruption_present: bool = False
    """True when at least one departure shows a delay or cancellation."""

    train_departure_count: int = 0
    """Total number of upcoming train departures returned by the source."""


def calculate_content_pressure_score(inputs: ContentPressureInputs) -> int:
    """Return the total content-pressure score for the given inputs.

    The score is the sum of per-factor contributions using :data:`SCORE_WEIGHTS`.
    The result is always non-negative.
    """
    score = 0
    score += (
        inputs.calendar_items_today_or_tomorrow
        * SCORE_WEIGHTS["calendar_item_today_or_tomorrow"]
    )
    score += inputs.calendar_items_later_week * SCORE_WEIGHTS["calendar_item_later_week"]
    score += inputs.trello_cards * SCORE_WEIGHTS["trello_card"]
    if inputs.weather_warning_present:
        score += SCORE_WEIGHTS["weather_warning"]
    if inputs.rain_or_storm_tomorrow:
        score += SCORE_WEIGHTS["rain_or_storm_tomorrow"]
    if inputs.waste_within_48h:
        score += SCORE_WEIGHTS["waste_within_48h"]
    if inputs.train_disruption_present:
        score += SCORE_WEIGHTS["train_disruption_or_delay"]
    if inputs.train_departure_count > 5:
        score += SCORE_WEIGHTS["train_departure_count_above_5"]
    return score


def select_display_mode(score: int) -> DisplayMode:
    """Return the :class:`DisplayMode` for the given content-pressure *score*.

    Boundaries:

    * score ≤ :data:`CALM_MAX_SCORE` → :attr:`DisplayMode.CALM`
    * score ≥ :data:`OVERLOADED_MIN_SCORE` → :attr:`DisplayMode.OVERLOADED`
    * otherwise → :attr:`DisplayMode.NORMAL`
    """
    if score <= CALM_MAX_SCORE:
        return DisplayMode.CALM
    if score >= OVERLOADED_MIN_SCORE:
        return DisplayMode.OVERLOADED
    return DisplayMode.NORMAL
