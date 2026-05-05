"""Tests for the content-pressure score calculation and display-mode selection.

These tests verify that:
- Each input factor contributes the correct weight.
- The combined score is deterministic.
- Mode boundaries are respected exactly.
- Edge cases (zero inputs, maximum inputs) are handled.
"""
from __future__ import annotations

import pytest

from epaper_dashboard_service.domain.content_pressure import (
    CALM_MAX_SCORE,
    OVERLOADED_MIN_SCORE,
    SCORE_WEIGHTS,
    ContentPressureInputs,
    DisplayMode,
    calculate_content_pressure_score,
    select_display_mode,
)


# ---------------------------------------------------------------------------
# Score calculation — individual factors
# ---------------------------------------------------------------------------


def test_empty_inputs_score_is_zero() -> None:
    inputs = ContentPressureInputs()
    assert calculate_content_pressure_score(inputs) == 0


def test_calendar_today_or_tomorrow_adds_correct_weight() -> None:
    inputs = ContentPressureInputs(calendar_items_today_or_tomorrow=1)
    assert calculate_content_pressure_score(inputs) == SCORE_WEIGHTS["calendar_item_today_or_tomorrow"]


def test_calendar_today_or_tomorrow_accumulates() -> None:
    inputs = ContentPressureInputs(calendar_items_today_or_tomorrow=3)
    assert calculate_content_pressure_score(inputs) == 3 * SCORE_WEIGHTS["calendar_item_today_or_tomorrow"]


def test_calendar_later_week_adds_correct_weight() -> None:
    inputs = ContentPressureInputs(calendar_items_later_week=1)
    assert calculate_content_pressure_score(inputs) == SCORE_WEIGHTS["calendar_item_later_week"]


def test_trello_card_adds_correct_weight() -> None:
    inputs = ContentPressureInputs(trello_cards=1)
    assert calculate_content_pressure_score(inputs) == SCORE_WEIGHTS["trello_card"]


def test_weather_warning_adds_correct_weight() -> None:
    inputs = ContentPressureInputs(weather_warning_present=True)
    assert calculate_content_pressure_score(inputs) == SCORE_WEIGHTS["weather_warning"]


def test_rain_or_storm_tomorrow_adds_correct_weight() -> None:
    inputs = ContentPressureInputs(rain_or_storm_tomorrow=True)
    assert calculate_content_pressure_score(inputs) == SCORE_WEIGHTS["rain_or_storm_tomorrow"]


def test_waste_within_48h_adds_correct_weight() -> None:
    inputs = ContentPressureInputs(waste_within_48h=True)
    assert calculate_content_pressure_score(inputs) == SCORE_WEIGHTS["waste_within_48h"]


def test_train_disruption_adds_correct_weight() -> None:
    inputs = ContentPressureInputs(train_disruption_present=True)
    assert calculate_content_pressure_score(inputs) == SCORE_WEIGHTS["train_disruption_or_delay"]


def test_train_departure_count_above_5_adds_weight() -> None:
    inputs = ContentPressureInputs(train_departure_count=6)
    assert calculate_content_pressure_score(inputs) == SCORE_WEIGHTS["train_departure_count_above_5"]


def test_train_departure_count_of_5_does_not_add_weight() -> None:
    """Exactly 5 departures must NOT trigger the above-5 bonus."""
    inputs = ContentPressureInputs(train_departure_count=5)
    assert calculate_content_pressure_score(inputs) == 0


def test_train_departure_count_of_4_does_not_add_weight() -> None:
    inputs = ContentPressureInputs(train_departure_count=4)
    assert calculate_content_pressure_score(inputs) == 0


# ---------------------------------------------------------------------------
# Score calculation — combined scenarios
# ---------------------------------------------------------------------------


def test_score_is_additive_across_independent_factors() -> None:
    """Multiple contributing factors must add up correctly."""
    inputs = ContentPressureInputs(
        calendar_items_today_or_tomorrow=1,   # 2
        calendar_items_later_week=2,          # 2
        trello_cards=3,                        # 3
    )
    expected = (
        1 * SCORE_WEIGHTS["calendar_item_today_or_tomorrow"]
        + 2 * SCORE_WEIGHTS["calendar_item_later_week"]
        + 3 * SCORE_WEIGHTS["trello_card"]
    )
    assert calculate_content_pressure_score(inputs) == expected


def test_all_boolean_flags_add_up() -> None:
    inputs = ContentPressureInputs(
        weather_warning_present=True,
        rain_or_storm_tomorrow=True,
        waste_within_48h=True,
        train_disruption_present=True,
    )
    expected = (
        SCORE_WEIGHTS["weather_warning"]
        + SCORE_WEIGHTS["rain_or_storm_tomorrow"]
        + SCORE_WEIGHTS["waste_within_48h"]
        + SCORE_WEIGHTS["train_disruption_or_delay"]
    )
    assert calculate_content_pressure_score(inputs) == expected


# ---------------------------------------------------------------------------
# Mode selection — boundary conditions
# ---------------------------------------------------------------------------


def test_score_zero_gives_calm_mode() -> None:
    assert select_display_mode(0) == DisplayMode.CALM


def test_score_at_calm_max_gives_calm_mode() -> None:
    assert select_display_mode(CALM_MAX_SCORE) == DisplayMode.CALM


def test_score_one_above_calm_max_gives_normal_mode() -> None:
    assert select_display_mode(CALM_MAX_SCORE + 1) == DisplayMode.NORMAL


def test_score_one_below_overloaded_min_gives_normal_mode() -> None:
    assert select_display_mode(OVERLOADED_MIN_SCORE - 1) == DisplayMode.NORMAL


def test_score_at_overloaded_min_gives_overloaded_mode() -> None:
    assert select_display_mode(OVERLOADED_MIN_SCORE) == DisplayMode.OVERLOADED


def test_score_above_overloaded_min_gives_overloaded_mode() -> None:
    assert select_display_mode(OVERLOADED_MIN_SCORE + 10) == DisplayMode.OVERLOADED


# ---------------------------------------------------------------------------
# Mode selection — realistic scenarios
# ---------------------------------------------------------------------------


def test_calm_day_quiet_household() -> None:
    """No events, no disruptions, no alerts → calm mode."""
    inputs = ContentPressureInputs(train_departure_count=3)
    score = calculate_content_pressure_score(inputs)
    assert select_display_mode(score) == DisplayMode.CALM


def test_normal_day_with_calendar_and_tasks() -> None:
    """A few calendar events and Trello cards → normal mode."""
    inputs = ContentPressureInputs(
        calendar_items_today_or_tomorrow=2,   # 4
        calendar_items_later_week=1,           # 1
        trello_cards=3,                        # 3
    )
    score = calculate_content_pressure_score(inputs)
    assert score == 8
    assert select_display_mode(score) == DisplayMode.NORMAL


def test_overloaded_day_with_warning_and_disruption() -> None:
    """Weather warning + train disruption + events → overloaded mode."""
    inputs = ContentPressureInputs(
        calendar_items_today_or_tomorrow=2,    # 4
        weather_warning_present=True,           # 4
        train_disruption_present=True,          # 4
    )
    score = calculate_content_pressure_score(inputs)
    assert score == 12
    # 12 is still normal (OVERLOADED_MIN_SCORE = 13)
    assert select_display_mode(score) == DisplayMode.NORMAL


def test_overloaded_day_pushes_above_threshold() -> None:
    """Many events + warning + disruption → overloaded mode."""
    inputs = ContentPressureInputs(
        calendar_items_today_or_tomorrow=3,    # 6
        calendar_items_later_week=2,            # 2
        weather_warning_present=True,           # 4
        train_disruption_present=True,          # 4
    )
    score = calculate_content_pressure_score(inputs)
    assert score == 16
    assert select_display_mode(score) == DisplayMode.OVERLOADED


def test_waste_and_storm_day() -> None:
    """Waste due + storm tomorrow is a high-pressure combination."""
    inputs = ContentPressureInputs(
        waste_within_48h=True,                 # 2
        rain_or_storm_tomorrow=True,           # 3
        calendar_items_today_or_tomorrow=1,    # 2
    )
    score = calculate_content_pressure_score(inputs)
    assert score == 7
    assert select_display_mode(score) == DisplayMode.NORMAL


def test_score_calculation_is_deterministic() -> None:
    """Calling the function twice with the same inputs must return the same score."""
    inputs = ContentPressureInputs(
        calendar_items_today_or_tomorrow=2,
        trello_cards=4,
        weather_warning_present=True,
    )
    assert calculate_content_pressure_score(inputs) == calculate_content_pressure_score(inputs)
