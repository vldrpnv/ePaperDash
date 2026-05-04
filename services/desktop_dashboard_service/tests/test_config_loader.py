"""Tests for the configuration loader — secrets substitution."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from epaper_dashboard_service.application.config import (
    ConfigurationError,
    load_configuration,
    load_secrets,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(tmp_path: Path, filename: str, content: str) -> Path:
    p = tmp_path / filename
    p.write_text(textwrap.dedent(content))
    return p


_MINIMAL_CONFIG = """\
    [layout]
    template = "layout.svg"
    width = 800
    height = 480

    [service]
    interval_seconds = 150

    [mqtt]
    host = "localhost"
    port = 1883
    topic = "epaper/image"
    client_id = "test"

    [[panels]]
    source = "calendar"
    renderer = "calendar_text"
    slot = "calendar"
    """


# ---------------------------------------------------------------------------
# load_secrets
# ---------------------------------------------------------------------------

def test_load_secrets_returns_string_values(tmp_path: Path) -> None:
    p = _write(tmp_path, "secrets.toml", """\
        [secrets]
        gcal_url = "https://example.com/cal.ics"
        waste_address = "Ringstr. 12"
        mqtt_password = "s3cret"
        """)
    result = load_secrets(p)
    assert result == {
        "gcal_url": "https://example.com/cal.ics",
        "waste_address": "Ringstr. 12",
        "mqtt_password": "s3cret",
    }


def test_load_secrets_empty_section(tmp_path: Path) -> None:
    p = _write(tmp_path, "secrets.toml", "[secrets]\n")
    assert load_secrets(p) == {}


def test_load_secrets_missing_section_returns_empty(tmp_path: Path) -> None:
    p = _write(tmp_path, "secrets.toml", "# no [secrets] section\n")
    assert load_secrets(p) == {}


# ---------------------------------------------------------------------------
# _substitute_secrets via load_configuration
# ---------------------------------------------------------------------------

def test_load_configuration_substitutes_placeholder_in_source_config(tmp_path: Path) -> None:
    cfg = _write(tmp_path, "config.toml", _MINIMAL_CONFIG + textwrap.dedent("""\
        [[panels]]
        source = "google_calendar"
        renderer = "google_calendar_text"
        slot = "gcal_events"
        [panels.source_config]
        calendar_url = "${gcal_url}"
        timezone = "Europe/Berlin"
        """))
    result = load_configuration(cfg, secrets={"gcal_url": "https://real.example.com/cal.ics"})
    gcal_panel = next(p for p in result.panels if p.slot == "gcal_events")
    assert gcal_panel.source_config["calendar_url"] == "https://real.example.com/cal.ics"


def test_load_configuration_no_secrets_leaves_placeholder_literal(tmp_path: Path) -> None:
    cfg = _write(tmp_path, "config.toml", _MINIMAL_CONFIG + textwrap.dedent("""\
        [[panels]]
        source = "google_calendar"
        renderer = "google_calendar_text"
        slot = "gcal_events"
        [panels.source_config]
        calendar_url = "${gcal_url}"
        """))
    # No secrets passed — placeholder survives unchanged
    result = load_configuration(cfg)
    gcal_panel = next(p for p in result.panels if p.slot == "gcal_events")
    assert gcal_panel.source_config["calendar_url"] == "${gcal_url}"


def test_load_configuration_raises_on_undefined_placeholder(tmp_path: Path) -> None:
    cfg = _write(tmp_path, "config.toml", _MINIMAL_CONFIG + textwrap.dedent("""\
        [[panels]]
        source = "google_calendar"
        renderer = "google_calendar_text"
        slot = "gcal_events"
        [panels.source_config]
        calendar_url = "${gcal_url}"
        """))
    with pytest.raises(ConfigurationError, match="gcal_url"):
        load_configuration(cfg, secrets={"other_key": "value"})


def test_load_configuration_substitutes_multiple_placeholders_in_one_value(tmp_path: Path) -> None:
    cfg = _write(tmp_path, "config.toml", _MINIMAL_CONFIG + textwrap.dedent("""\
        [[panels]]
        source = "google_calendar"
        renderer = "google_calendar_text"
        slot = "gcal_events"
        [panels.source_config]
        calendar_url = "https://${host}/cal/${id}.ics"
        """))
    result = load_configuration(cfg, secrets={"host": "example.com", "id": "abc123"})
    gcal_panel = next(p for p in result.panels if p.slot == "gcal_events")
    assert gcal_panel.source_config["calendar_url"] == "https://example.com/cal/abc123.ics"


def test_load_configuration_substitutes_mqtt_password(tmp_path: Path) -> None:
    cfg = _write(tmp_path, "config.toml", """\
        [layout]
        template = "layout.svg"
        width = 800
        height = 480

        [service]
        interval_seconds = 150

        [mqtt]
        host = "broker.example.com"
        port = 1883
        topic = "epaper/image"
        client_id = "test"
        username = "user"
        password = "${mqtt_password}"

        [[panels]]
        source = "calendar"
        renderer = "calendar_text"
        slot = "calendar"
        """)
    result = load_configuration(cfg, secrets={"mqtt_password": "s3cret"})
    assert result.mqtt.password == "s3cret"


def test_example_dashboard_config_substitutes_secret_waste_address() -> None:
    config_path = Path(__file__).resolve().parents[1] / "examples" / "dashboard_config.toml"

    result = load_configuration(
        config_path,
        secrets={
            "gcal_url": "https://example.com/calendar.ics",
            "waste_address": "Ringstr. 12",
            "trello_api_key": "example-trello-key",
            "trello_token": "example-trello-token",
        },
    )

    waste_panel = next(p for p in result.panels if p.slot == "waste")
    assert waste_panel.source_config["address"] == "Ringstr. 12"
