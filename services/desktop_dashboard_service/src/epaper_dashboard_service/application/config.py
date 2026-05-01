from __future__ import annotations

import re
from pathlib import Path
import tomllib
from typing import Any

from epaper_dashboard_service.domain.models import (
    DashboardConfiguration,
    LayoutConfig,
    MqttConfig,
    PanelDefinition,
    ServiceConfig,
)


class ConfigurationError(ValueError):
    pass


_PLACEHOLDER_RE = re.compile(r"\$\{([^}]+)\}")


def load_configuration(
    config_path: Path,
    secrets: dict[str, str] | None = None,
) -> DashboardConfiguration:
    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)

    if secrets:
        raw = _substitute_secrets(raw, secrets)

    try:
        layout_section = raw["layout"]
        mqtt_section = raw["mqtt"]
        panels_section = raw["panels"]
    except KeyError as error:
        raise ConfigurationError(f"Missing configuration section: {error.args[0]}") from error

    layout = LayoutConfig(
        template=_resolve_path(config_path, layout_section["template"]),
        width=int(layout_section.get("width", 800)),
        height=int(layout_section.get("height", 480)),
        preview_output=_resolve_optional_path(config_path, layout_section.get("preview_output")),
    )
    mqtt = MqttConfig(
        host=mqtt_section["host"],
        port=int(mqtt_section.get("port", 1883)),
        topic=mqtt_section["topic"],
        client_id=mqtt_section.get("client_id", "epaper-dashboard-service"),
        username=mqtt_section.get("username"),
        password=mqtt_section.get("password"),
        qos=int(mqtt_section.get("qos", 1)),
        retain=bool(mqtt_section.get("retain", True)),
        publish_retry_attempts=int(mqtt_section.get("publish_retry_attempts", 3)),
        publish_retry_delay_seconds=float(mqtt_section.get("publish_retry_delay_seconds", 1.0)),
    )
    panels = tuple(
        PanelDefinition(
            source=panel["source"],
            renderer=panel["renderer"],
            slot=panel["slot"],
            source_config=dict(panel.get("source_config", {})),
            renderer_config=dict(panel.get("renderer_config", {})),
        )
        for panel in panels_section
    )
    if not panels:
        raise ConfigurationError("At least one panel must be configured")

    service_section = raw.get("service", {})
    service = ServiceConfig(
        interval_seconds=int(service_section.get("interval_seconds", 300)),
    )

    return DashboardConfiguration(layout=layout, mqtt=mqtt, panels=panels, service=service)


def _resolve_path(config_path: Path, candidate: str) -> str:
    return str((config_path.parent / candidate).resolve())


def _resolve_optional_path(config_path: Path, candidate: str | None) -> str | None:
    if candidate is None:
        return None
    return _resolve_path(config_path, candidate)


def load_secrets(secrets_path: Path) -> dict[str, str]:
    """Load a ``[secrets]`` TOML file and return its key→value mapping.

    Only string values directly under the ``[secrets]`` table are accepted.
    """
    with secrets_path.open("rb") as handle:
        raw = tomllib.load(handle)
    secrets_section = raw.get("secrets", {})
    return {k: str(v) for k, v in secrets_section.items()}


def _substitute_secrets(obj: Any, secrets: dict[str, str]) -> Any:
    """Recursively replace ``${key}`` placeholders in all string values."""
    if isinstance(obj, str):
        def _replace(match: re.Match) -> str:
            key = match.group(1)
            if key not in secrets:
                raise ConfigurationError(
                    f"Config references undefined secret: ${{{key}}}. "
                    f"Available secrets: {sorted(secrets)}"
                )
            return secrets[key]
        return _PLACEHOLDER_RE.sub(_replace, obj)
    if isinstance(obj, dict):
        return {k: _substitute_secrets(v, secrets) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_substitute_secrets(item, secrets) for item in obj]
    return obj
