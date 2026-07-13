#!/usr/bin/env zsh

set -euo pipefail

# Daily JTrack -> Juseless sync wrapper.
#
# What this does:
#   - Runs the same safe sync operation as sync_jtrack_to_juseless.py --apply.
#   - Saves each published local JTrack DataLad dataset.
#   - Creates/updates the Juseless bare repo.
#   - Pushes and verifies the dataset.
#   - Updates the readable Juseless mirror.
#   - Writes/updates study_activity migration_sync rows with dataset_id.
#   - Deletes the local JTrack study folder only after verified sync succeeds.
#   - Skips local deletion when the study has active/syncing activity rows.
#
# How to schedule at a particular time with cron, example for every day at 02:30:
#   30 2 * * * /path/to/eCRF/eCRF_backend/scripts/daily_sync_jtrack_to_juseless.zsh
#
# Optional environment overrides:
#   CASEE_APP_ROOT   Repository/app root containing .env.
#   CASEE_PYTHON     Python executable. Defaults to hosted/bin/python if present.
#   CASEE_SYNC_LOG_DIR
#                    Directory for daily sync logs. Defaults to <app>/logs.
#   CASEE_SYNC_LOCK_DIR
#                    Lock directory. Defaults to <app>/.daily-sync-juseless.lock.
#
# Production notes:
#   - Put the absolute script path in cron/systemd.
#   - The OS user running this script must be the same service user, or at least
#     have access to .env, ecrf.db, BIDS_ROOT, DataLad, Git, and SSH keys.
#   - SSH key auth should be non-interactive. The backend sets BatchMode=yes
#     when ECRF_JUSELESS_SSH_PASSWORD is empty.

SCRIPT_DIR="${0:A:h}"
DEFAULT_APP_ROOT="${SCRIPT_DIR:h:h}"
APP_ROOT="${CASEE_APP_ROOT:-$DEFAULT_APP_ROOT}"

if [[ ! -d "$APP_ROOT" ]]; then
  echo "[daily-sync] App root does not exist: $APP_ROOT" >&2
  exit 2
fi

cd "$APP_ROOT"

if [[ -n "${CASEE_PYTHON:-}" ]]; then
  PYTHON_BIN="$CASEE_PYTHON"
elif [[ -x "$APP_ROOT/hosted/bin/python" ]]; then
  PYTHON_BIN="$APP_ROOT/hosted/bin/python"
else
  PYTHON_BIN="${PYTHON_BIN:-python3}"
fi

LOG_DIR="${CASEE_SYNC_LOG_DIR:-$APP_ROOT/logs}"
LOCK_DIR="${CASEE_SYNC_LOCK_DIR:-$APP_ROOT/.daily-sync-juseless.lock}"
DATE_BIN="${DATE_BIN:-date}"
MKDIR_BIN="${MKDIR_BIN:-mkdir}"
RMDIR_BIN="${RMDIR_BIN:-rmdir}"
TEE_BIN="${TEE_BIN:-tee}"

"$MKDIR_BIN" -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/jtrack-to-juseless-sync-$("$DATE_BIN" '+%Y-%m-%d').log"

log() {
  echo "[daily-sync] $("$DATE_BIN" '+%Y-%m-%d %H:%M:%S') $*"
}

if ! "$MKDIR_BIN" "$LOCK_DIR" 2>/dev/null; then
  log "Another daily sync is already running; exiting." | "$TEE_BIN" -a "$LOG_FILE"
  exit 0
fi

cleanup() {
  "$RMDIR_BIN" "$LOCK_DIR" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

{
  log "Starting JTrack -> Juseless daily sync"
  log "App root: $APP_ROOT"
  log "Python: $PYTHON_BIN"
  set +e
  "$PYTHON_BIN" -m eCRF_backend.scripts.sync_jtrack_to_juseless --apply --delete-local
  status=$?
  set -e
  if [[ $status -eq 0 ]]; then
    log "Completed JTrack -> Juseless daily sync successfully"
  else
    log "JTrack -> Juseless daily sync failed with status=$status"
  fi
  exit $status
} 2>&1 | "$TEE_BIN" -a "$LOG_FILE"
