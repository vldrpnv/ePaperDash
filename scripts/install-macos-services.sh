#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MQTT_DIR="$HOME/services/mqtt_simple"
MQTT_CONFIG="$MQTT_DIR/mosquitto.conf"
MQTT_DATA_DIR="$MQTT_DIR/data"
SECRETS_FILE=${EPAPERDASH_SECRETS:-"$ROOT_DIR/secrets.toml"}
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
LOG_DIR="$HOME/Library/Logs/ePaperDash"
UV_BIN=$(command -v uv || true)
MOSQUITTO_BIN=$(command -v mosquitto || true)

if [ -z "$UV_BIN" ] || [ -z "$MOSQUITTO_BIN" ]; then
    echo "Install uv and Mosquitto before installing the LaunchAgents." >&2
    exit 2
fi
if [ ! -f "$SECRETS_FILE" ]; then
    echo "Missing secrets file: $SECRETS_FILE" >&2
    echo "Copy secrets.example.toml to secrets.toml and fill in your credentials." >&2
    exit 2
fi
if [ ! -f "$MQTT_CONFIG" ]; then
    echo "Missing Mosquitto config: $MQTT_CONFIG" >&2
    echo "Install and configure Mosquitto before installing the LaunchAgents." >&2
    exit 2
fi

mkdir -p "$LAUNCH_AGENTS" "$LOG_DIR" "$MQTT_DATA_DIR"
chmod 700 "$LOG_DIR" "$MQTT_DATA_DIR"

python3 - "$MQTT_CONFIG" "$MQTT_DATA_DIR" <<'PY'
from pathlib import Path
import sys

config_path = Path(sys.argv[1])
data_dir = Path(sys.argv[2]).resolve()
lines = config_path.read_text().splitlines()
updated = []
found = False
for line in lines:
    if line.lstrip().startswith("persistence_location "):
        updated.append(f"persistence_location {data_dir}/")
        found = True
    else:
        updated.append(line)
if not found:
    try:
        index = next(i for i, line in enumerate(updated) if line.strip() == "persistence true") + 1
    except StopIteration:
        updated.append("persistence true")
        index = len(updated)
    updated.insert(index, f"persistence_location {data_dir}/")
config_path.write_text("\n".join(updated) + "\n")
PY

uv sync --project "$ROOT_DIR" --locked
DASHBOARD_BIN="$ROOT_DIR/.venv/bin/epaper-dashboard-service"
if [ ! -x "$DASHBOARD_BIN" ]; then
    echo "Dashboard executable was not installed at $DASHBOARD_BIN" >&2
    exit 5
fi

python3 - "$ROOT_DIR" "$DASHBOARD_BIN" "$MOSQUITTO_BIN" "$MQTT_CONFIG" "$SECRETS_FILE" "$LOG_DIR" "$LAUNCH_AGENTS" <<'PY'
from pathlib import Path
import plistlib
import sys

root, dashboard_bin, mosquitto, mqtt_config, secrets, logs, agents = map(Path, sys.argv[1:])
services = {
    "com.vladi.epaperdash.mosquitto": {
        "ProgramArguments": [str(mosquitto), "-c", str(mqtt_config)],
        "WorkingDirectory": str(mqtt_config.parent),
        "StandardOutPath": str(logs / "mosquitto.log"),
        "StandardErrorPath": str(logs / "mosquitto.log"),
    },
    "com.vladi.epaperdash.dashboard": {
        "ProgramArguments": [
            str(dashboard_bin),
            "--config", str(root / "services/desktop_dashboard_service/examples/dashboard_config.toml"),
            "--secrets", str(secrets),
        ],
        "WorkingDirectory": str(root),
        "StandardOutPath": str(logs / "dashboard.log"),
        "StandardErrorPath": str(logs / "dashboard.log"),
        "EnvironmentVariables": {
            "HOME": str(Path.home()),
            "PATH": "/opt/homebrew/bin:/opt/homebrew/sbin:/usr/bin:/bin",
            "PYTHONUNBUFFERED": "1",
        },
    },
}

for label, settings in services.items():
    plist = {
        "Label": label,
        **settings,
        "RunAtLoad": True,
        "KeepAlive": True,
        "ThrottleInterval": 10,
    }
    path = agents / f"{label}.plist"
    with path.open("wb") as handle:
        plistlib.dump(plist, handle, sort_keys=False)
    path.chmod(0o644)
PY

LAUNCHD_UID=$(id -u)
DOMAIN="gui/$LAUNCHD_UID"
MOSQUITTO_LABEL="com.vladi.epaperdash.mosquitto"
DASHBOARD_LABEL="com.vladi.epaperdash.dashboard"

launchctl bootout "$DOMAIN/$MOSQUITTO_LABEL" 2>/dev/null || true
launchctl bootout "$DOMAIN/$DASHBOARD_LABEL" 2>/dev/null || true

if lsof -nP -iTCP:1883 -sTCP:LISTEN 2>/dev/null | tail -n +2 | grep -q .; then
    echo "Port 1883 is still occupied by an unmanaged process. Stop it, then rerun this installer." >&2
    exit 3
fi

launchctl bootstrap "$DOMAIN" "$LAUNCH_AGENTS/$MOSQUITTO_LABEL.plist"

attempt=0
until nc -z 127.0.0.1 1883; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 20 ]; then
        echo "Mosquitto did not begin listening on port 1883." >&2
        exit 4
    fi
    sleep 1
done

launchctl bootstrap "$DOMAIN" "$LAUNCH_AGENTS/$DASHBOARD_LABEL.plist"

echo "Installed and started Mosquitto and ePaperDash as user LaunchAgents."
