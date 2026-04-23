from __future__ import annotations

from datetime import datetime, timezone

from epaper_dashboard_service.adapters.rendering.train import TrainDepartureTextRenderer
from epaper_dashboard_service.domain.models import (
    PanelDefinition,
    TextSpan,
    TrainDeparture,
    TrainDepartures,
)


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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_renderer_produces_single_text_block() -> None:
    renderer = TrainDepartureTextRenderer()
    data = TrainDepartures(station_name="Eichenau", entries=())
    blocks = renderer.render(data, _make_panel())
    assert len(blocks) == 1
    assert blocks[0].slot == "trains"


def test_renderer_header_line_is_station_name() -> None:
    renderer = TrainDepartureTextRenderer()
    data = TrainDepartures(station_name="Eichenau", entries=())
    blocks = renderer.render(data, _make_panel())
    assert blocks[0].lines[0] == "Eichenau"


def test_renderer_on_time_departure_shows_bold_label_and_scheduled_time() -> None:
    renderer = TrainDepartureTextRenderer()
    dep = TrainDeparture(
        line="S4",
        destination="Leuchtenbergring",
        scheduled_time=_dt(10, 0),
        actual_time=_dt(10, 0),  # same → no extra time shown
        cancelled=False,
    )
    data = TrainDepartures(station_name="Eichenau", entries=(dep,))
    blocks = renderer.render(data, _make_panel())

    rich_line = blocks[0].lines[1]
    assert isinstance(rich_line, tuple)
    label_span = rich_line[0]
    assert isinstance(label_span, TextSpan)
    assert label_span.text == "S4"
    assert label_span.bold is True
    assert not label_span.strikethrough
    time_texts = [s.text for s in rich_line]
    assert "10:00" in time_texts
    # on-time: actual == scheduled → actual time not repeated
    assert time_texts.count("10:00") == 1


def test_renderer_delayed_departure_shows_both_times() -> None:
    renderer = TrainDepartureTextRenderer()
    dep = TrainDeparture(
        line="S4",
        destination="Leuchtenbergring",
        scheduled_time=_dt(10, 0),
        actual_time=_dt(10, 3),
        cancelled=False,
    )
    data = TrainDepartures(station_name="Eichenau", entries=(dep,))
    blocks = renderer.render(data, _make_panel())

    rich_line = blocks[0].lines[1]
    assert isinstance(rich_line, tuple)
    time_texts = [s.text.strip() for s in rich_line]
    assert "10:00" in time_texts
    assert "10:03" in time_texts


def test_renderer_cancelled_departure_has_strikethrough_and_status() -> None:
    renderer = TrainDepartureTextRenderer()
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
    assert isinstance(rich_line, tuple)
    struck = [s for s in rich_line if s.strikethrough]
    assert len(struck) == 1
    assert "10:15" in struck[0].text
    all_text = "".join(s.text for s in rich_line)
    assert "Cancelled" in all_text


def test_renderer_cancelled_departure_label_is_bold_not_strikethrough() -> None:
    renderer = TrainDepartureTextRenderer()
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
    label_span = rich_line[0]
    assert label_span.text == "S3"
    assert label_span.bold is True
    assert label_span.strikethrough is False


def test_renderer_passes_through_renderer_config_attributes() -> None:
    renderer = TrainDepartureTextRenderer()
    data = TrainDepartures(station_name="Eichenau", entries=())
    blocks = renderer.render(data, _make_panel(**{"font-size": "20", "fill": "black"}))
    assert blocks[0].attributes == {"font-size": "20", "fill": "black"}


def test_renderer_multiple_entries_produce_multiple_lines() -> None:
    renderer = TrainDepartureTextRenderer()
    deps = tuple(
        TrainDeparture(
            line="S4",
            destination="Leuchtenbergring",
            scheduled_time=_dt(10, i),
            actual_time=_dt(10, i),
            cancelled=False,
        )
        for i in range(3)
    )
    data = TrainDepartures(station_name="Eichenau", entries=deps)
    blocks = renderer.render(data, _make_panel())
    # 1 header + 3 entries
    assert len(blocks[0].lines) == 4
