#!/bin/sh
set -eu

SERVICE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SERVICE_DIR/../.." && pwd)
exec "$REPO_ROOT/run-dashboard.sh" "$@"
