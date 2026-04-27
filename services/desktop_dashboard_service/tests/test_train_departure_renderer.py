from __future__ import annotations

from datetime import datetime, timezone

from epaper_dashboard_service.adapters.rendering.train import TrainDepartureTextRenderer
from epaper_dashboard_service.domain.models import (
    PanelDefinition,
    StyledLine,
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
    header = blocks[0].lines[0]
    # Station header is now a bold RichLine
    assert isinstance(header, tuple)
    assert header[0].text == "Eichenau"


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
    assert isinstance(rich_line, StyledLine)
    label_span = rich_line.spans[0]
    assert isinstance(label_span, TextSpan)
    assert label_span.text == "S4"
    assert label_span.bold is True
    assert not label_span.strikethrough
    time_texts = [s.text for s in rich_line.spans]
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
    assert isinstance(rich_line, StyledLine)
    time_texts = [s.text.strip() for s in rich_line.spans]
    assert "10:00" in time_texts
    assert "10:03" in time_texts


def test_renderer_delayed_departure_has_strikethrough_on_scheduled_time() -> None:
    renderer = TrainDepartureTextRenderer()
    dep = TrainDeparture(
        line="S4",
        destination="Leuchtenbergring",
        scheduled_time=_dt(10, 0),
        actual_time=_dt(10, 5),
        cancelled=False,
    )
    data = TrainDepartures(station_name="Eichenau", entries=(dep,))
    blocks = renderer.render(data, _make_panel())

    rich_line = blocks[0].lines[1]
    assert isinstance(rich_line, StyledLine)
    scheduled_spans = [s for s in rich_line.spans if "10:00" in s.text]
    assert len(scheduled_spans) == 1
    assert scheduled_spans[0].strikethrough is True


def test_renderer_on_time_departure_scheduled_time_not_strikethrough() -> None:
    renderer = TrainDepartureTextRenderer()
    dep = TrainDeparture(
        line="S4",
        destination="Leuchtenbergring",
        scheduled_time=_dt(10, 0),
        actual_time=_dt(10, 0),
        cancelled=False,
    )
    data = TrainDepartures(station_name="Eichenau", entries=(dep,))
    blocks = renderer.render(data, _make_panel())

    rich_line = blocks[0].lines[1]
    assert isinstance(rich_line, StyledLine)
    scheduled_spans = [s for s in rich_line.spans if "10:00" in s.text]
    assert all(not s.strikethrough for s in scheduled_spans)


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
    assert isinstance(rich_line, StyledLine)
    struck = [s for s in rich_line.spans if s.strikethrough]
    assert len(struck) == 1
    assert "10:15" in struck[0].text
    all_text = "".join(s.text for s in rich_line.spans)
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
    label_span = rich_line.spans[0]
    assert label_span.text == "S3"
    assert label_span.bold is True
    assert label_span.strikethrough is False


def test_renderer_passes_through_renderer_config_attributes() -> None:
    renderer = TrainDepartureTextRenderer()
    data = TrainDepartures(station_name="Eichenau", entries=())
    blocks = renderer.render(data, _make_panel(**{"font-size": "20", "fill": "black"}))
    assert blocks[0].attributes == {"font-size": "20", "fill": "black"}


def test_renderer_shows_destination_after_label_on_time() -> None:
    renderer = TrainDepartureTextRenderer()
    dep = TrainDeparture(
        line="S4",
        destination="Leuchtenbergring",
        scheduled_time=_dt(10, 0),
        actual_time=_dt(10, 0),
        cancelled=False,
    )
    data = TrainDepartures(station_name="Eichenau", entries=(dep,))
    blocks = renderer.render(data, _make_panel())

    # Main departure line: lines[1] — contains label + time but NOT destination
    rich_line = blocks[0].lines[1]
    assert isinstance(rich_line, StyledLine)
    all_main_text = "".join(s.text for s in rich_line.spans)
    assert "S4" in all_main_text
    assert "10:00" in all_main_text
    # Destination is on its own sub-line: lines[2]
    dest_line = blocks[0].lines[2]
    assert isinstance(dest_line, StyledLine)
    assert "Leuchtenbergring" in dest_line.spans[0].text


def test_renderer_shows_destination_after_label_delayed() -> None:
    renderer = TrainDepartureTextRenderer()
    dep = TrainDeparture(
        line="S4",
        destination="Leuchtenbergring",
        scheduled_time=_dt(10, 0),
        actual_time=_dt(10, 5),
        cancelled=False,
    )
    data = TrainDepartures(station_name="Eichenau", entries=(dep,))
    blocks = renderer.render(data, _make_panel())

    rich_line = blocks[0].lines[1]
    all_text = "".join(s.text for s in rich_line.spans)
    assert "10:00" in all_text
    assert "10:05" in all_text
    dest_line = blocks[0].lines[2]
    assert isinstance(dest_line, StyledLine)
    assert "Leuchtenbergring" in dest_line.spans[0].text


def test_renderer_shows_destination_after_label_cancelled() -> None:
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
    all_text = "".join(s.text for s in rich_line.spans)
    assert "10:15" in all_text
    dest_line = blocks[0].lines[2]
    assert isinstance(dest_line, StyledLine)
    assert "Holzkirchen" in dest_line.spans[0].text


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
    # 1 header + 3 entries × 2 lines (main + destination) = 7
    assert len(blocks[0].lines) == 7


# ---------------------------------------------------------------------------
# Station bold
# ---------------------------------------------------------------------------

def test_renderer_station_header_is_bold_rich_line() -> None:
    renderer = TrainDepartureTextRenderer()
    data = TrainDepartures(station_name="Eichenau", entries=())
    blocks = renderer.render(data, _make_panel())
    header = blocks[0].lines[0]
    assert isinstance(header, tuple), "Station header must be a RichLine (tuple of TextSpan)"
    assert header[0].text == "Eichenau"
    assert header[0].bold is True


# ---------------------------------------------------------------------------
# departure-font-size renderer_config key
# ---------------------------------------------------------------------------

def test_renderer_departure_line_is_styled_line_when_font_size_configured() -> None:
    renderer = TrainDepartureTextRenderer()
    dep = TrainDeparture(
        line="S4",
        destination="Leuchtenbergring",
        scheduled_time=_dt(10, 0),
        actual_time=_dt(10, 0),
        cancelled=False,
    )
    data = TrainDepartures(station_name="Eichenau", entries=(dep,))
    blocks = renderer.render(data, _make_panel(**{"departure-font-size": "18"}))

    departure_line = blocks[0].lines[1]
    assert isinstance(departure_line, StyledLine), "Departure line must be a StyledLine when departure-font-size is set"
    assert departure_line.font_size == 18


def test_renderer_departure_line_is_styled_line_without_font_size_when_not_configured() -> None:
    renderer = TrainDepartureTextRenderer()
    dep = TrainDeparture(
        line="S4",
        destination="Leuchtenbergring",
        scheduled_time=_dt(10, 0),
        actual_time=_dt(10, 0),
        cancelled=False,
    )
    data = TrainDepartures(station_name="Eichenau", entries=(dep,))
    blocks = renderer.render(data, _make_panel())

    departure_line = blocks[0].lines[1]
    assert isinstance(departure_line, StyledLine)
    assert departure_line.font_size is None


def test_renderer_departure_font_size_not_passed_to_block_attributes() -> None:
    """departure-font-size must not appear in block SVG attributes — it is consumed internally."""
    renderer = TrainDepartureTextRenderer()
    data = TrainDepartures(station_name="Eichenau", entries=())
    blocks = renderer.render(data, _make_panel(**{"departure-font-size": "18", "fill": "black"}))
    assert "departure-font-size" not in blocks[0].attributes


# ---------------------------------------------------------------------------
# Destination font size matches departure line font size
# ---------------------------------------------------------------------------

def test_renderer_dest_line_has_same_font_size_as_departure_line() -> None:
    """Destination line must share the departure-font-size so both lines render the same size."""
    renderer = TrainDepartureTextRenderer()
    dep = TrainDeparture(
        line="S4",
        destination="Leuchtenbergring",
        scheduled_time=_dt(10, 0),
        actual_time=_dt(10, 0),
        cancelled=False,
    )
    data = TrainDepartures(station_name="Eichenau", entries=(dep,))
    blocks = renderer.render(data, _make_panel(**{"departure-font-size": "18"}))

    main_line = blocks[0].lines[1]
    dest_line = blocks[0].lines[2]
    assert isinstance(main_line, StyledLine)
    assert isinstance(dest_line, StyledLine)
    assert main_line.font_size == dest_line.font_size


def test_renderer_dest_font_size_none_when_departure_font_size_not_configured() -> None:
    renderer = TrainDepartureTextRenderer()
    dep = TrainDeparture(
        line="S4",
        destination="Leuchtenbergring",
        scheduled_time=_dt(10, 0),
        actual_time=_dt(10, 0),
        cancelled=False,
    )
    data = TrainDepartures(station_name="Eichenau", entries=(dep,))
    blocks = renderer.render(data, _make_panel())
    dest_line = blocks[0].lines[2]
    assert isinstance(dest_line, StyledLine)
    assert dest_line.font_size is None


# ---------------------------------------------------------------------------
# Line spacing — dy values
# ---------------------------------------------------------------------------

def _three_departure_block():
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
    return renderer.render(data, _make_panel())[0]


def test_renderer_first_departure_uses_station_break_dy() -> None:
    block = _three_departure_block()
    first_main = block.lines[1]
    assert isinstance(first_main, StyledLine)
    assert first_main.dy == "1.6em"


def test_renderer_subsequent_departures_use_departure_break_dy() -> None:
    block = _three_departure_block()
    second_main = block.lines[3]
    third_main = block.lines[5]
    assert isinstance(second_main, StyledLine)
    assert isinstance(third_main, StyledLine)
    assert second_main.dy == "1.8em"
    assert third_main.dy == "1.8em"


def test_renderer_destination_lines_use_tight_dy() -> None:
    block = _three_departure_block()
    for dest_idx in (2, 4, 6):
        dest_line = block.lines[dest_idx]
        assert isinstance(dest_line, StyledLine)
        assert dest_line.dy == "1.1em"


def test_renderer_break_dy_configurable_via_renderer_config() -> None:
    renderer = TrainDepartureTextRenderer()
    dep = TrainDeparture(
        line="S4",
        destination="Leuchtenbergring",
        scheduled_time=_dt(10, 0),
        actual_time=_dt(10, 0),
        cancelled=False,
    )
    data = TrainDepartures(station_name="Eichenau", entries=(dep, dep))
    blocks = renderer.render(
        data,
        _make_panel(**{"station-break-dy": "2em", "departure-break-dy": "2.5em"}),
    )
    assert blocks[0].lines[1].dy == "2em"    # first main line — station break
    assert blocks[0].lines[3].dy == "2.5em"  # second main line — departure break
