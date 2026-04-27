from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from epaper_dashboard_service.domain.models import ClockTime
from epaper_dashboard_service.domain.ports import SourcePlugin


class ClockSourcePlugin(SourcePlugin):
    """Return the current wall-clock time in the configured timezone.

    ``source_config`` keys:
    - ``timezone``: IANA timezone name (default: ``"UTC"``).
    """

    name = "clock"

    def fetch(self, config: dict[str, object]) -> ClockTime:
        timezone_name = str(config.get("timezone", "UTC"))
        now = datetime.now(ZoneInfo(timezone_name))
        return ClockTime(current_time=now)
