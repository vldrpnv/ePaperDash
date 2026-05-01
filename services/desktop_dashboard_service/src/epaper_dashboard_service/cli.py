from __future__ import annotations

import argparse
import hashlib
import logging
import time
from pathlib import Path

from epaper_dashboard_service.application.config import load_configuration, load_secrets
from epaper_dashboard_service.bootstrap import build_application


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate and publish an ePaper dashboard image, cycling at a configurable interval"
    )
    parser.add_argument("--config", required=True, type=Path, help="Path to the TOML configuration file")
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Override the check interval in seconds (default: value from config, or 300)",
    )
    parser.add_argument(
        "--secrets",
        type=Path,
        default=None,
        metavar="PATH",
        help="Path to a secrets.toml file whose [secrets] values substitute ${key} placeholders in the config",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable DEBUG logging for all service components",
    )
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    secrets: dict[str, str] | None = None
    if args.secrets is not None:
        secrets = load_secrets(args.secrets.resolve())

    configuration = load_configuration(args.config.resolve(), secrets=secrets)
    interval_seconds = args.interval or configuration.service.interval_seconds
    application = build_application(configuration.mqtt)

    print(f"Starting dashboard service (interval={interval_seconds}s, log_level={logging.getLevelName(log_level)})")

    last_payload_hash: str | None = None
    try:
        while True:
            try:
                result = application.generate(configuration)
                current_hash = hashlib.sha256(result.payload).hexdigest()

                if current_hash != last_payload_hash:
                    application.publish(result.payload)
                    last_payload_hash = current_hash
                    print(f"Published {len(result.payload)} bytes to {configuration.mqtt.topic} (hash={current_hash[:8]})")
                else:
                    print("Dashboard unchanged, skipping publish")
            except Exception as error:
                print(f"Cycle failed: {error}")

            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\nStopped")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
