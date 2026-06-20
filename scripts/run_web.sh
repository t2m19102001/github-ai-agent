#!/usr/bin/env bash
# Boot the GitHub AI Agent web surface (FastAPI) on localhost, one command.
#
# Uses safe local defaults: mock LLM, SQLite, no Postgres/Redis required.
# Reads .env if present (created from .env.example); falls back to built-in
# defaults otherwise.
#
# Usage:
#   bash scripts/run_web.sh                 # 127.0.0.1:8000, reload on
#   HOST=0.0.0.0 PORT=9000 bash scripts/run_web.sh
#   RELOAD=0 bash scripts/run_web.sh        # disable auto-reload
#
# Exit codes:
#   0  server exited cleanly
#   1  prerequisite missing (venv / uvicorn)
#   2  port already in use

set -euo pipefail

# Resolve repo root from this script's location so it works from anywhere.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
RELOAD="${RELOAD:-1}"

# Prefer the project venv; fall back to whatever python3 is on PATH.
if [ -x ".venv/bin/python" ]; then
    PY=".venv/bin/python"
else
    echo "warning: .venv not found; using system python3" >&2
    PY="python3"
fi

if ! "${PY}" -c "import uvicorn, fastapi" >/dev/null 2>&1; then
    echo "error: uvicorn/fastapi not installed in ${PY}." >&2
    echo "       Run: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt" >&2
    exit 1
fi

# Fail fast on a busy port instead of letting uvicorn die with a stack trace.
if command -v lsof >/dev/null 2>&1 && lsof -ti:"${PORT}" >/dev/null 2>&1; then
    echo "error: port ${PORT} is already in use. Stop the other process or set PORT." >&2
    exit 2
fi

RELOAD_FLAG=""
if [ "${RELOAD}" = "1" ]; then
    RELOAD_FLAG="--reload"
fi

echo "Starting web surface on http://${HOST}:${PORT}  (docs: /docs, health: /health)"
exec "${PY}" -m uvicorn src.web.main:app \
    --host "${HOST}" \
    --port "${PORT}" \
    ${RELOAD_FLAG} \
    --log-level info
