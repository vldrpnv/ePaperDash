"""Tests for the i18n / locale translation infrastructure."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from epaper_dashboard_service.adapters.i18n import GERMAN, LOCALES, get_translations
from epaper_dashboard_service.adapters.rendering.train import TrainDepartureTextRenderer
from epaper_dashboard_service.adapters.rendering.weather import _select_weather_blocks
from epaper_dashboard_service.adapters.sources.calendar import CalendarSourcePlugin
from epaper_dashboard_service.domain.i18n import ENGLISH, Translations
from epaper_dashboard_service.domain.models import (
    PanelDefinition,
    StyledLine,
    TrainDeparture,
    TrainDepartures,
    WeatherPeriod,
)


# ---------------------------------------------------------------------------
# Translations dataclass
# ---------------------------------------------------------------------------

def test_translations_defaults_are_english() -> None:
    tr = Translations()
    assert tr.cancelled == "Cancelled"
    assert tr.tomorrow == "Tomorrow"
    assert tr.tomorrow_short == "tmrw"
    assert tr.last_update == "Last update"
    assert tr.day_names == ()
    assert tr.month_names == ()
    assert tr.condition_labels == {}


def test_translations_condition_passthrough_when_no_mapping() -> None:
    tr = Translations()
    assert tr.condition("Sunny") == "Sunny"
    assert tr.condition("Unknown label") == "Unknown label"


def test_translations_condition_returns_localized_label() -> None:
    tr = Translations(condition_labels={"Sunny": "Sonnig", "Cloudy": "Bewölkt"})
    assert tr.condition("Sunny") == "Sonnig"
    assert tr.condition("Cloudy") == "Bewölkt"
    # Falls back for unmapped labels
    assert tr.condition("Rain") == "Rain"


# ---------------------------------------------------------------------------
# get_translations / locale registry
# ---------------------------------------------------------------------------

def test_get_translations_returns_english_for_en() -> None:
    assert get_translations("en") is ENGLISH


def test_get_translations_returns_german_for_de() -> None:
    assert get_translations("de") is GERMAN


def test_get_translations_falls_back_to_english_for_unknown_locale() -> None:
    result = get_translations("xx")
    assert result is ENGLISH


def test_locales_dict_contains_en_and_de() -> None:
    assert "en" in LOCALES
    assert "de" in LOCALES


# ---------------------------------------------------------------------------
# German translations — spot checks
# ---------------------------------------------------------------------------

def test_german_cancelled_label() -> None:
    assert GERMAN.cancelled == "Entfällt"


def test_german_tomorrow_label() -> None:
    assert GERMAN.tomorrow == "Morgen"


def test_german_tomorrow_short_label() -> None:
    assert GERMAN.tomorrow_short == "mo"


def test_german_last_update_label() -> None:
    assert GERMAN.last_update == "Letzte Aktualisierung"


def test_german_day_names_has_seven_entries() -> None:
    assert len(GERMAN.day_names) == 7


def test_german_month_names_has_twelve_entries() -> None:
    assert len(GERMAN.month_names) == 12


def test_german_day_names_monday_first() -> None:
    assert GERMAN.day_names[0] == "Montag"


def test_german_month_names_january_first() -> None:
    assert GERMAN.month_names[0] == "Januar"


def test_german_condition_sunny_translates() -> None:
    assert GERMAN.condition("Sunny") == "Sonnig"


def test_german_condition_cloudy_translates() -> None:
    assert GERMAN.condition("Cloudy") == "Bewölkt"


def test_german_condition_thunderstorm_translates() -> None:
    assert GERMAN.condition("Thunderstorm") == "Gewitter"


# ---------------------------------------------------------------------------
# TrainDepartureTextRenderer — German "Cancelled" label
# ---------------------------------------------------------------------------

def _make_panel(**renderer_config) -> PanelDefinition:
    return PanelDefinition(
        source="mvg_departures",
        renderer="train_departures_text",
        slot="trains",
        source_config={},
        renderer_config=renderer_config,
    )


def _dt(h: int, m: int) -> datetime:
    return datetime(2024, 5, 3, h, m, tzinfo=timezone.utc)


def test_german_renderer_cancelled_shows_german_label() -> None:
    renderer = TrainDepartureTextRenderer(translations=GERMAN)
    dep = TrainDeparture(
        line="S3",
        destination="Holzkirchen",
        scheduled_time=_dt(10, 15),
        actual_time=None,
        cancelled=True,
    )
    data = TrainDepartures(station_name="Eichenau", entries=(dep,))
    blocks = renderer.render(data, _make_panel())

    rich_line = blocks[0].lines[1]
    assert isinstance(rich_line, StyledLine)
    all_text = "".join(s.text for s in rich_line.spans)
    assert "Entfällt" in all_text
    assert "Cancelled" not in all_text


def test_english_renderer_cancelled_shows_english_label() -> None:
    renderer = TrainDepartureTextRenderer(translations=ENGLISH)
    dep = TrainDeparture(
        line="S3",
        destination="Holzkirchen",
        scheduled_time=_dt(10, 15),
        actual_time=None,
        cancelled=True,
    )
    data = TrainDepartures(station_name="Eichenau", entries=(dep,))
    blocks = renderer.render(data, _make_panel())

    rich_line = blocks[0].lines[1]
    all_text = "".join(s.text for s in rich_line.spans)
    assert "Cancelled" in all_text
    assert "Entfällt" not in all_text


# ---------------------------------------------------------------------------
# CalendarSourcePlugin — German day and month names
# ---------------------------------------------------------------------------

def test_calendar_source_german_day_name(monkeypatch) -> None:
    """CalendarSourcePlugin with German translations returns a German weekday name."""
    from datetime import date

    # Freeze "now" to a known Monday
    class _FakeDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            # 2024-04-01 is a Monday (weekday=0)
            return cls(2024, 4, 1, 10, 0, 0, tzinfo=tz)

    monkeypatch.setattr(
        "epaper_dashboard_service.adapters.sources.calendar.datetime",
        _FakeDatetime,
    )

    plugin = CalendarSourcePlugin(translations=GERMAN)
    result = plugin.fetch({"timezone": "UTC"})
    assert result.day_of_week == "Montag"


def test_calendar_source_german_month_name(monkeypatch) -> None:
    """CalendarSourcePlugin with German translations returns a German month name."""

    class _FakeDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            # 2024-03-15 is in March → "März"
            return cls(2024, 3, 15, 10, 0, 0, tzinfo=tz)

    monkeypatch.setattr(
        "epaper_dashboard_service.adapters.sources.calendar.datetime",
        _FakeDatetime,
    )

    plugin = CalendarSourcePlugin(translations=GERMAN)
    result = plugin.fetch({"timezone": "UTC"})
    assert result.month == "März"


def test_calendar_source_english_day_name_with_default_format(monkeypatch) -> None:
    """CalendarSourcePlugin without translations uses strftime %A (English)."""

    class _FakeDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2024, 4, 1, 10, 0, 0, tzinfo=tz)  # Monday

    monkeypatch.setattr(
        "epaper_dashboard_service.adapters.sources.calendar.datetime",
        _FakeDatetime,
    )

    plugin = CalendarSourcePlugin(translations=ENGLISH)
    result = plugin.fetch({"timezone": "UTC"})
    assert result.day_of_week == "Monday"


def test_calendar_source_custom_format_bypasses_translations(monkeypatch) -> None:
    """When day_of_week_format is not %A, translations are not used."""

    class _FakeDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2024, 4, 1, 10, 0, 0, tzinfo=tz)  # Monday

    monkeypatch.setattr(
        "epaper_dashboard_service.adapters.sources.calendar.datetime",
        _FakeDatetime,
    )

    plugin = CalendarSourcePlugin(translations=GERMAN)
    # %a gives abbreviated English name when locale not overridden
    result = plugin.fetch({"timezone": "UTC", "day_of_week_format": "%a"})
    # strftime %a on C locale gives "Mon" for Monday — translations must NOT override
    assert result.day_of_week == "Mon"


# ---------------------------------------------------------------------------
# _select_weather_blocks — German "tmrw" / "mo" prefix
# ---------------------------------------------------------------------------

def _make_weather_period(day: str, hour: int) -> WeatherPeriod:
    start = datetime.fromisoformat(f"{day}T{hour:02d}:00:00+00:00")
    return WeatherPeriod(
        start_time=start,
        end_time=start,
        temperature_c=10.0,
        precipitation_probability_percent=0,
        condition_label="Sunny",
        condition_icon="\u2600",
    )


def _make_two_day_periods(base_date: str, next_date: str) -> tuple[WeatherPeriod, ...]:
    return tuple(
        _make_weather_period(base_date, h) for h in range(24)
    ) + tuple(
        _make_weather_period(next_date, h) for h in range(24)
    )


def test_select_weather_blocks_german_uses_tomorrow_short_mo() -> None:
    """Blocks crossing midnight should be labelled with the German 'mo' prefix."""
    # Use 22:00 local time so the third block crosses midnight
    now = datetime(2026, 4, 27, 22, 0, 0, tzinfo=timezone.utc)
    periods = _make_two_day_periods("2026-04-27", "2026-04-28")
    blocks = _select_weather_blocks(periods, now, GERMAN)
    tomorrow_labels = [b.time_label for b in blocks if b.time_label.startswith("mo ")]
    assert len(tomorrow_labels) >= 1


def test_select_weather_blocks_english_uses_tmrw_prefix() -> None:
    """Blocks crossing midnight should be labelled with the English 'tmrw' prefix."""
    now = datetime(2026, 4, 27, 22, 0, 0, tzinfo=timezone.utc)
    periods = _make_two_day_periods("2026-04-27", "2026-04-28")
    blocks = _select_weather_blocks(periods, now, ENGLISH)
    tomorrow_labels = [b.time_label for b in blocks if b.time_label.startswith("tmrw ")]
    assert len(tomorrow_labels) >= 1


# ---------------------------------------------------------------------------
# DashboardApplicationService — localized "Last update" label
# ---------------------------------------------------------------------------

def test_application_service_german_last_update_label(tmp_path: Path) -> None:
    """DashboardApplicationService with German translations emits German last_update prefix."""
    from PIL import Image

    from epaper_dashboard_service.application.service import (
        DashboardApplicationService,
        PluginRegistry,
    )
    from epaper_dashboard_service.domain.models import (
        DashboardConfiguration,
        LayoutConfig,
        MqttConfig,
    )
    from epaper_dashboard_service.domain.ports import DashboardPublisher, LayoutRenderer

    class FakeLayoutRenderer(LayoutRenderer):
        def __init__(self) -> None:
            self.blocks: tuple = ()

        def render(self, template_path, blocks, width, height, cleared_slots=(), svg_output=None):
            self.blocks = blocks
            return Image.new("L", (width, height), color=255)

    class FakePublisher(DashboardPublisher):
        def publish(self, payload: bytes) -> None:
            pass

    template = tmp_path / "layout.svg"
    template.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="800" height="480">
          <text id="last_update" x="8" y="476" />
        </svg>""",
        encoding="utf-8",
    )

    layout_renderer = FakeLayoutRenderer()
    service = DashboardApplicationService(
        registry=PluginRegistry(sources=(), renderers=()),
        layout_renderer=layout_renderer,
        publisher=FakePublisher(),
        translations=GERMAN,
    )
    configuration = DashboardConfiguration(
        layout=LayoutConfig(template=str(template), width=800, height=480),
        mqtt=MqttConfig(host="localhost", port=1883, topic="epaper/image"),
        panels=(),
    )

    service.generate(configuration)

    last_update_blocks = [b for b in layout_renderer.blocks if b.slot == "last_update"]
    assert len(last_update_blocks) == 1
    assert last_update_blocks[0].lines[0].startswith("Letzte Aktualisierung: ")


def test_application_service_english_last_update_label(tmp_path: Path) -> None:
    """DashboardApplicationService with English translations emits English last_update prefix."""
    from PIL import Image

    from epaper_dashboard_service.application.service import (
        DashboardApplicationService,
        PluginRegistry,
    )
    from epaper_dashboard_service.domain.models import (
        DashboardConfiguration,
        LayoutConfig,
        MqttConfig,
    )
    from epaper_dashboard_service.domain.ports import DashboardPublisher, LayoutRenderer

    class FakeLayoutRenderer(LayoutRenderer):
        def __init__(self) -> None:
            self.blocks: tuple = ()

        def render(self, template_path, blocks, width, height, cleared_slots=(), svg_output=None):
            self.blocks = blocks
            return Image.new("L", (width, height), color=255)

    class FakePublisher(DashboardPublisher):
        def publish(self, payload: bytes) -> None:
            pass

    template = tmp_path / "layout.svg"
    template.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="800" height="480">
          <text id="last_update" x="8" y="476" />
        </svg>""",
        encoding="utf-8",
    )

    layout_renderer = FakeLayoutRenderer()
    service = DashboardApplicationService(
        registry=PluginRegistry(sources=(), renderers=()),
        layout_renderer=layout_renderer,
        publisher=FakePublisher(),
        translations=ENGLISH,
    )
    configuration = DashboardConfiguration(
        layout=LayoutConfig(template=str(template), width=800, height=480),
        mqtt=MqttConfig(host="localhost", port=1883, topic="epaper/image"),
        panels=(),
    )

    service.generate(configuration)

    last_update_blocks = [b for b in layout_renderer.blocks if b.slot == "last_update"]
    assert len(last_update_blocks) == 1
    assert last_update_blocks[0].lines[0].startswith("Last update: ")
