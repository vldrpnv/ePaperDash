from __future__ import annotations

import argparse
from pathlib import Path

from epaper_dashboard_service.application.config import load_configuration
from epaper_dashboard_service.bootstrap import build_application


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate and publish an ePaper dashboard image")
    parser.add_argument("--config", required=True, type=Path, help="Path to the TOML configuration file")
    args = parser.parse_args()

    configuration = load_configuration(args.config.resolve())
    application = build_application(configuration.mqtt)
    result = application.generate_and_publish(configuration)
    print(f"Generated {len(result.payload)} bytes for MQTT topic {configuration.mqtt.topic}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
