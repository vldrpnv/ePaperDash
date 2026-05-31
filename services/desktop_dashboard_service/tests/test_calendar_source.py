from __future__ import annotations

from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from epaper_dashboard_service.adapters.sources.calendar import CalendarSourcePlugin


def test_calendar_source_fetch_default_config() -> None:
    # Mock datetime.now to return a fixed timestamp
    # 2025-05-20 is a Tuesday
    fixed_now = datetime(2025, 5, 20, 12, 0, 0, tzinfo=ZoneInfo("UTC"))

    with patch("epaper_dashboard_service.adapters.sources.calendar.datetime") as mock_datetime:
        mock_datetime.now.return_value = fixed_now

        plugin = CalendarSourcePlugin()
        result = plugin.fetch({})

        assert result.day == 20
        assert result.day_of_week == "Tuesday"
        assert result.month == "May"
        mock_datetime.now.assert_called_once_with(ZoneInfo("UTC"))


def test_calendar_source_fetch_custom_timezone() -> None:
    # 2025-05-20 00:30 UTC is 2025-05-20 02:30 CEST
    fixed_now_utc = datetime(2025, 5, 20, 0, 30, 0, tzinfo=ZoneInfo("UTC"))
    fixed_now_berlin = fixed_now_utc.astimezone(ZoneInfo("Europe/Berlin"))

    with patch("epaper_dashboard_service.adapters.sources.calendar.datetime") as mock_datetime:
        # We need to make sure datetime.now(ZoneInfo("Europe/Berlin")) returns the expected time
        mock_datetime.now.side_effect = lambda tz: fixed_now_utc.astimezone(tz)

        plugin = CalendarSourcePlugin()
        result = plugin.fetch({"timezone": "Europe/Berlin"})

        assert result.day == 20
        assert result.day_of_week == "Tuesday"
        assert result.month == "May"
        # In this specific case it's still the same day, but we verified the timezone was passed
        mock_datetime.now.assert_called_with(ZoneInfo("Europe/Berlin"))


def test_calendar_source_fetch_custom_formats() -> None:
    # 2025-06-20 is a Friday
    fixed_now = datetime(2025, 6, 20, 12, 0, 0, tzinfo=ZoneInfo("UTC"))

    with patch("epaper_dashboard_service.adapters.sources.calendar.datetime") as mock_datetime:
        mock_datetime.now.return_value = fixed_now

        plugin = CalendarSourcePlugin()
        result = plugin.fetch(
            {
                "day_of_week_format": "%a",
                "month_format": "%b",
            }
        )

    assert result.day == 20
    assert result.day_of_week == "Fri"
    assert result.month == "Jun"
