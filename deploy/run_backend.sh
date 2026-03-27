#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/opt/casee}"
VENV_PATH="${VENV_PATH:-${APP_ROOT}/.venv}"
ENV_FILE="${ENV_FILE:-${APP_ROOT}/.env}"

cd "$APP_ROOT"

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

"${VENV_PATH}/bin/python" -m eCRF_backend.preflight
exec "${VENV_PATH}/bin/uvicorn" eCRF_backend.datalad_main:app \
  --host "${ECRF_BIND_HOST:-127.0.0.1}" \
  --port "${ECRF_PORT:-8000}" \
  --log-level info