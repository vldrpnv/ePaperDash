#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SECRETS_FILE=${EPAPERDASH_SECRETS:-"$ROOT_DIR/secrets.toml"}

if [ ! -f "$SECRETS_FILE" ]; then
    echo "Missing secrets file: $SECRETS_FILE" >&2
    echo "Copy secrets.example.toml to secrets.toml and fill in your credentials." >&2
    exit 2
fi

exec uv run --project "$ROOT_DIR" epaper-dashboard-service \
    --config "$ROOT_DIR/services/desktop_dashboard_service/examples/dashboard_config.toml" \
    --secrets "$SECRETS_FILE" \
    "$@"
