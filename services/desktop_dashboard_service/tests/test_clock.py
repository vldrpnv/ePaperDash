from __future__ import annotations

import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from epaper_dashboard_service.adapters.rendering.clock import ClockTextRenderer
from epaper_dashboard_service.adapters.sources.clock import ClockSourcePlugin
from epaper_dashboard_service.domain.models import ClockTime, PanelDefinition


def _make_panel(**renderer_config) -> PanelDefinition:
    return PanelDefinition(
        source="clock",
        renderer="clock_text",
        slot="clock",
        source_config={},
        renderer_config=renderer_config,
    )


# ──────────────────────── source plugin ────────────────────────


class TestClockSourcePlugin:
    def test_returns_clock_time_instance(self) -> None:
        plugin = ClockSourcePlugin()
        result = plugin.fetch({})
        assert isinstance(result, ClockTime)

    def test_name(self) -> None:
        assert ClockSourcePlugin.name == "clock"

    def test_defaults_to_utc_when_no_timezone_configured(self) -> None:
        plugin = ClockSourcePlugin()
        result = plugin.fetch({})
        assert result.current_time.tzinfo is not None
        assert result.current_time.utcoffset().total_seconds() == 0

    def test_honours_configured_timezone(self) -> None:
        plugin = ClockSourcePlugin()
        result = plugin.fetch({"timezone": "America/New_York"})
        assert result.current_time.tzinfo is not None
        # New York is UTC-5 or UTC-4; just verify the tzinfo key matches
        assert "America/New_York" in str(result.current_time.tzinfo)

    def test_raises_on_invalid_timezone(self) -> None:
        plugin = ClockSourcePlugin()
        with pytest.raises(Exception):
            plugin.fetch({"timezone": "Not/A/Timezone"})


# ──────────────────────── renderer plugin ────────────────────────


class TestClockTextRenderer:
    def _fixed_clock(self, hour: int = 14, minute: int = 30) -> ClockTime:
        return ClockTime(current_time=datetime(2026, 4, 27, hour, minute, 0, tzinfo=timezone.utc))

    def test_name(self) -> None:
        assert ClockTextRenderer.name == "clock_text"

    def test_supported_type(self) -> None:
        assert ClockTextRenderer.supported_type is ClockTime

    def test_default_format_hhmm(self) -> None:
        renderer = ClockTextRenderer()
        data = self._fixed_clock(14, 30)
        blocks = renderer.render(data, _make_panel())
        assert len(blocks) == 1
        assert blocks[0].lines == ("14:30",)

    def test_custom_time_format(self) -> None:
        renderer = ClockTextRenderer()
        data = self._fixed_clock(9, 5)
        blocks = renderer.render(data, _make_panel(time_format="%I:%M %p"))
        assert blocks[0].lines == ("09:05 AM",)

    def test_slot_matches_panel_slot(self) -> None:
        renderer = ClockTextRenderer()
        panel = PanelDefinition(
            source="clock",
            renderer="clock_text",
            slot="my_clock_slot",
            source_config={},
            renderer_config={},
        )
        blocks = renderer.render(self._fixed_clock(), panel)
        assert blocks[0].slot == "my_clock_slot"

    def test_text_attributes_passed_through(self) -> None:
        renderer = ClockTextRenderer()
        data = self._fixed_clock()
        blocks = renderer.render(data, _make_panel(**{"font-size": "72", "fill": "black"}))
        assert blocks[0].attributes == {"font-size": "72", "fill": "black"}

    def test_unknown_renderer_config_keys_ignored(self) -> None:
        renderer = ClockTextRenderer()
        data = self._fixed_clock()
        # time_format and unknown_key should not appear in attributes
        blocks = renderer.render(data, _make_panel(time_format="%H:%M", unknown_key="x"))
        assert "time_format" not in blocks[0].attributes
        assert "unknown_key" not in blocks[0].attributes

    def test_returns_tuple(self) -> None:
        renderer = ClockTextRenderer()
        result = renderer.render(self._fixed_clock(), _make_panel())
        assert isinstance(result, tuple)
        assert len(result) == 1
