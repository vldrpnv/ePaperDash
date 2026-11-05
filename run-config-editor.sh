#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec uv run --project "$ROOT_DIR" python -m config_editor_app.main "$@"
