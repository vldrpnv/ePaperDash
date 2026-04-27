from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from epaper_dashboard_service.domain.models import ClockData
from epaper_dashboard_service.domain.ports import SourcePlugin


class ClockSourcePlugin(SourcePlugin):
    """Source plugin that returns the current time as ``ClockData``.

    Configuration keys (all optional):
    - ``timezone``: IANA timezone name (default ``"UTC"``).
    """

    name = "clock"

    def fetch(self, config: dict[str, object]) -> ClockData:
        timezone_name = str(config.get("timezone", "UTC"))
        render_time = datetime.now(ZoneInfo(timezone_name))
        return ClockData(render_time=render_time)
