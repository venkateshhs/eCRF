#!/usr/bin/env bash
set -euo pipefail

cd /app

echo "[case-e] backend entrypoint starting"

# -----------------------------------
# Git identity (REQUIRED for DataLad)
# -----------------------------------
GIT_NAME="${ECRF_DATALAD_GIT_NAME:-case-e}"
GIT_EMAIL="${ECRF_DATALAD_GIT_EMAIL:-case-e@localhost}"

git config --global user.name "$GIT_NAME"
git config --global user.email "$GIT_EMAIL"

echo "[case-e] git identity set: $GIT_NAME <$GIT_EMAIL>"

# -----------------------------------
# Directories
# -----------------------------------
mkdir -p "${ECRF_DATA_DIR:-/srv/casee}"
mkdir -p "${BIDS_ROOT:-/srv/casee/bids_datasets}"
mkdir -p /ria-store

# -----------------------------------
# Init RIA store (if needed)
# -----------------------------------
if [ ! -f /ria-store/ria-layout-version ]; then
  echo "[case-e] initializing RIA store root"
  printf "1\n" > /ria-store/ria-layout-version
fi

# -----------------------------------
# Preflight
# -----------------------------------
python -m eCRF_backend.preflight

echo "[case-e] starting uvicorn"

exec uvicorn eCRF_backend.datalad_main:app \
  --host "${ECRF_BIND_HOST:-0.0.0.0}" \
  --port "${ECRF_PORT:-8000}" \
  --log-level info