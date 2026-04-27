from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from epaper_dashboard_service.domain.i18n import ENGLISH, Translations
from epaper_dashboard_service.domain.models import CalendarDate
from epaper_dashboard_service.domain.ports import SourcePlugin


class CalendarSourcePlugin(SourcePlugin):
    name = "calendar"

    def __init__(self, translations: Translations | None = None) -> None:
        self._translations = translations or ENGLISH

    def fetch(self, config: dict[str, object]) -> CalendarDate:
        timezone_name = str(config.get("timezone", "UTC"))
        timestamp = datetime.now(ZoneInfo(timezone_name))
        day_of_week_format = str(config.get("day_of_week_format", "%A"))
        month_format = str(config.get("month_format", "%B"))

        tr = self._translations
        if day_of_week_format == "%A" and tr.day_names:
            day_of_week = tr.day_names[timestamp.weekday()]
        else:
            day_of_week = timestamp.strftime(day_of_week_format)

        if month_format == "%B" and tr.month_names:
            month = tr.month_names[timestamp.month - 1]
        else:
            month = timestamp.strftime(month_format)

        return CalendarDate(
            day_of_week=day_of_week,
            day=timestamp.day,
            month=month,
        )
