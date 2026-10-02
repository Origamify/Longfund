#!/usr/bin/env bash
cd "$(dirname "$0")" || exit 1
PY=".venv/bin/python"
[ -x "$PY" ] || PY="python3"
exec "$PY" -m pytest "$@"
