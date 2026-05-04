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
    ProfileDefinition,
    ProfilePanelDefinition,
    ServiceConfig,
    SourceDefinition,
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
    except KeyError as error:
        raise ConfigurationError(f"Missing configuration section: {error.args[0]}") from error

    template = layout_section.get("template")
    if template:
        template = _resolve_path(config_path, template)

    layout = LayoutConfig(
        width=int(layout_section.get("width", 800)),
        height=int(layout_section.get("height", 480)),
        preview_output=_resolve_optional_path(config_path, layout_section.get("preview_output")),
        template=template,
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

    # Parse legacy 'panels' structure if it exists
    panels_section = raw.get("panels", [])
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

    # Parse new 'sources' structure if it exists
    sources_section = raw.get("sources", [])
    sources = tuple(
        SourceDefinition(
            id=source["id"],
            source=source["source"],
            source_config=dict(source.get("source_config", {})),
        )
        for source in sources_section
    )

    # Parse new 'profiles' structure if it exists
    profiles_section = raw.get("profiles", [])
    profiles = tuple(
        ProfileDefinition(
            id=profile["id"],
            start_time=profile["start_time"],
            template=_resolve_path(config_path, profile["template"]),
            panels=tuple(
                ProfilePanelDefinition(
                    source_id=panel["source_id"],
                    renderer=panel["renderer"],
                    slot=panel["slot"],
                    renderer_config=dict(panel.get("renderer_config", {})),
                )
                for panel in profile.get("panels", [])
            )
        )
        for profile in profiles_section
    )

    if not panels and not profiles:
        raise ConfigurationError("At least one legacy panel or one profile must be configured")

    service_section = raw.get("service", {})
    service = ServiceConfig(
        interval_seconds=int(service_section.get("interval_seconds", 300)),
    )

    return DashboardConfiguration(
        layout=layout,
        mqtt=mqtt,
        panels=panels,
        sources=sources,
        profiles=profiles,
        service=service
    )


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
