from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from epaper_dashboard_service.domain.models import CalendarDate
from epaper_dashboard_service.domain.ports import SourcePlugin


class CalendarSourcePlugin(SourcePlugin):
    name = "calendar"

    def fetch(self, config: dict[str, object]) -> CalendarDate:
        timezone_name = str(config.get("timezone", "UTC"))
        timestamp = datetime.now(ZoneInfo(timezone_name))
        return CalendarDate(
            day_of_week=timestamp.strftime(str(config.get("day_of_week_format", "%A"))),
            day=timestamp.day,
            month=timestamp.strftime(str(config.get("month_format", "%B"))),
        )
