# Juseless Integration Runbook

This document is the one-stop production checklist for integrating Case-E/JTrack with Juseless using DataLad.

The intended production behavior is:

- JTrack stores active/local study folders under `BIDS_ROOT`.
- Each study is synced to one bare Git/DataLad repository on Juseless.
- A readable worktree mirror is also maintained on Juseless so admins can inspect actual files.
- Local JTrack study folders are removed only after remote sync and verification succeed.
- If Juseless is unavailable, local data remains in JTrack and sync is retried later.

## 1. Production Paths

Decide the final paths before first deployment.

Example JTrack server paths:

```env
ECRF_DATA_DIR=/var/www/ecrf.inm7.de/www/casee
BIDS_ROOT=/var/www/ecrf.inm7.de/www/casee/bids_datasets
ECRF_DATABASE_URL=sqlite:////var/www/ecrf.inm7.de/www/casee/ecrf.db
ECRF_TEMPLATES_DIR=/var/www/ecrf.inm7.de/www/casee/templates
```

Example Juseless paths:

```env
ECRF_DATALAD_SSH_REMOTE_TEMPLATE=ssh://casee@juseless.inm7.de/data/project/JTrack/CaseE/bids_datasets/{study}.git
ECRF_JUSELESS_STUDIES_DIR=/data/project/JTrack/CaseE/studies
```

`{study}` is replaced by the local dataset folder name, for example:

```text
study_12_Heart_Study
```

So the bare repo becomes:

```text
/data/project/JTrack/CaseE/bids_datasets/study_12_Heart_Study.git
```

And the readable mirror becomes:

```text
/data/project/JTrack/CaseE/studies/study_12_Heart_Study
```

## 2. SSH Access

Production should use SSH key authentication, not passwords.

On the JTrack server, the OS user running Case-E must be able to SSH to Juseless non-interactively:

```bash
ssh casee@juseless.inm7.de
```

or for the production account:

```bash
ssh jfischer@juseless.inm7.de
```

The command must not ask for a password.

In production `.env`, leave password empty:

```env
ECRF_JUSELESS_SSH_PASSWORD=
```

When this value is empty, the backend uses SSH key mode with `BatchMode=yes`, so it fails fast instead of waiting for a password prompt.

Password mode is only for local testing:

```env
ECRF_JUSELESS_SSH_PASSWORD=example-password
```

If password mode is used, `sshpass` must be installed. Do not use password mode for hosted production.

## 3. Required `.env` Values

Update these values in the production `.env` file at the app root.

Core runtime:

```env
ECRF_ENV=production
ECRF_PROFILE=server
ECRF_BIND_HOST=127.0.0.1
ECRF_PORT=8000
ECRF_OPEN_BROWSER=0
```

Storage and database:

```env
ECRF_DATA_DIR=/var/www/ecrf.inm7.de/www/casee
BIDS_ROOT=/var/www/ecrf.inm7.de/www/casee/bids_datasets
ECRF_DATABASE_URL=sqlite:////var/www/ecrf.inm7.de/www/casee/ecrf.db
ECRF_TEMPLATES_DIR=/var/www/ecrf.inm7.de/www/casee/templates
```

Security:

```env
ECRF_SECRET_KEY=<strong-random-production-secret>
ECRF_JWT_ALGORITHM=HS256
ECRF_PASSWORD_HASHING_ENABLED=1
ECRF_CORS_ALLOW_ORIGINS=https://ecrf.inm7.de
```

Admin bootstrap:

```env
ECRF_BOOTSTRAP_ADMIN=1
ECRF_ADMIN_USERNAME=admin
ECRF_ADMIN_EMAIL=<admin-email>
ECRF_ADMIN_PASSWORD=<temporary-production-admin-password>
ECRF_ADMIN_FIRST_NAME=Admin
ECRF_ADMIN_LAST_NAME=User
ECRF_ADMIN_ROLE=Administrator
```

After the first production admin is created, consider setting:

```env
ECRF_BOOTSTRAP_ADMIN=0
```

DataLad/Juseless:

```env
ECRF_DATALAD_MODE=primary
ECRF_DATALAD_SYNC_MODE=sync
ECRF_DATALAD_GIT_NAME=case-e service
ECRF_DATALAD_GIT_EMAIL=case-e@example.org
ECRF_DATALAD_PUSH_ON_SAVE=0
ECRF_DATALAD_PUSH_DATA_MODE=auto-if-wanted
ECRF_DATALAD_VERIFY_PUSH=1
ECRF_DATALAD_DROP_AFTER_PUSH=0
ECRF_DATALAD_GET_ON_OPEN=1
ECRF_DATALAD_SSH_REMOTE_TEMPLATE=ssh://casee@juseless.inm7.de/data/project/JTrack/CaseE/bids_datasets/{study}.git
ECRF_JUSELESS_MIRROR_AFTER_PUSH=1
ECRF_JUSELESS_STUDIES_DIR=/data/project/JTrack/CaseE/studies
ECRF_JUSELESS_SSH_PASSWORD=
ECRF_DATALAD_RIA_NAME=ria
ECRF_DATALAD_REQUIRE_RIA_FOR_WRITES=1
ECRF_DATALAD_GPGSIGN=0
ECRF_DATALAD_GPG_KEYID=
ECRF_DATALAD_LOCK_TIMEOUT_SECONDS=120
ECRF_STUDY_ACTIVITY_SYNC_INTERVAL_SECONDS=300
```

Important notes:

- `ECRF_DATALAD_PUSH_ON_SAVE=0` means normal save does not push immediately.
- Logout/background/daily sync performs the verified push to Juseless.
- `ECRF_DATALAD_VERIFY_PUSH=1` must stay enabled for safety.
- `ECRF_JUSELESS_MIRROR_AFTER_PUSH=1` keeps readable files visible on Juseless.
- `ECRF_DATALAD_DROP_AFTER_PUSH=0` keeps annex content in the local dataset until the whole local folder is safely removed by cleanup.

## 4. Juseless Directory Setup

On Juseless, create the repository and readable mirror roots.

Example:

```bash
mkdir -p /data/project/JTrack/CaseE/bids_datasets
mkdir -p /data/project/JTrack/CaseE/studies
```

Make sure the SSH user from `ECRF_DATALAD_SSH_REMOTE_TEMPLATE` can read/write both directories:

```bash
chown -R casee:casee /data/project/JTrack/CaseE
chmod -R u+rwX,g+rwX /data/project/JTrack/CaseE
```

Adjust user/group to the real production service account.

## 5. First Deployment Checks

From the JTrack app root:

```bash
hosted/bin/python -m eCRF_backend.preflight
```

Then start the backend and check:

```bash
curl http://127.0.0.1:8000/health
```

The health response should show DataLad enabled/configured.

Also check that the backend user can reach Juseless:

```bash
ssh casee@juseless.inm7.de true
```

This must finish without prompting for a password.

## 6. Initial One-Time Migration

Use this when production already has local JTrack study folders that were not yet synced to Juseless or do not have `study_activity` rows.

Before migration:

1. Put the site in maintenance mode.
2. Back up the database:

```bash
cp /var/www/ecrf.inm7.de/www/casee/ecrf.db /var/www/ecrf.inm7.de/www/casee/ecrf.db.before-juseless-migration
```

3. Snapshot or back up `BIDS_ROOT`.

Dry-run first:

```bash
cd /path/to/eCRF
hosted/bin/python -m eCRF_backend.scripts.sync_jtrack_to_juseless
```

This changes nothing. Inspect candidates, skipped studies, orphan folders, and ambiguous folders.

Apply to one study first:

```bash
hosted/bin/python -m eCRF_backend.scripts.sync_jtrack_to_juseless --apply --study-id 12
```

Verify on Juseless:

```bash
ls /data/project/JTrack/CaseE/bids_datasets/study_12_*.git
ls /data/project/JTrack/CaseE/studies/study_12_*
```

Verify the readable mirror contains expected files:

```bash
find /data/project/JTrack/CaseE/studies/study_12_* -maxdepth 3 -type f | head
```

Apply to all published studies, but keep local folders:

```bash
hosted/bin/python -m eCRF_backend.scripts.sync_jtrack_to_juseless --apply
```

Only after this has been verified, delete local JTrack folders after verified sync:

```bash
hosted/bin/python -m eCRF_backend.scripts.sync_jtrack_to_juseless --apply --delete-local
```

Safety behavior:

- Dry-run is default.
- Missing or ambiguous folders are skipped.
- Failed studies keep local JTrack data.
- Local folders are deleted only after save, push, verification, readable mirror update, and `study_activity` update succeed.
- Local deletion is skipped if active/syncing activity rows exist.

## 7. Normal Runtime Sync

During normal app use:

1. Study data is written to local JTrack under `BIDS_ROOT`.
2. `study_activity` records which sessions touched which studies.
3. On manual logout or auto logout, inactive/released studies are synced to Juseless.
4. After verified sync succeeds, local JTrack study folder is removed.
5. If sync fails, the folder is retained and the row becomes `sync_failed`.
6. Background cleanup retries later.

The background retry interval is:

```env
ECRF_STUDY_ACTIVITY_SYNC_INTERVAL_SECONDS=300
```

Set to `0` only if background cleanup should be disabled.

## 8. Daily Scheduled Sync

Use the wrapper:

```text
eCRF_backend/scripts/daily_sync_jtrack_to_juseless.zsh
```

This runs:

```bash
hosted/bin/python -m eCRF_backend.scripts.sync_jtrack_to_juseless --apply --delete-local
```

It logs to:

```text
<app-root>/logs/jtrack-to-juseless-sync-YYYY-MM-DD.log
```

Example cron entry for every day at 02:30:

```cron
30 2 * * * /path/to/eCRF/eCRF_backend/scripts/daily_sync_jtrack_to_juseless.zsh
```

If cron runs as a different OS user, set explicit overrides:

```cron
30 2 * * * CASEE_APP_ROOT=/path/to/eCRF CASEE_PYTHON=/path/to/eCRF/hosted/bin/python /path/to/eCRF/eCRF_backend/scripts/daily_sync_jtrack_to_juseless.zsh
```

The cron user must have access to:

- app root and `.env`
- `ecrf.db`
- `BIDS_ROOT`
- DataLad and Git
- SSH key for Juseless
- Juseless destination directories

## 9. Delete Behavior

When a study is deleted from the app:

- The local JTrack folder for that specific study is removed.
- The Juseless bare repo for that specific study is removed.
- The readable Juseless mirror for that specific study is removed.
- DB rows are removed.

Safety expectations:

- Deletion uses study-id-specific paths.
- It refuses unexpected/non-study paths.
- If Juseless delete fails, a pending remote delete is recorded and retried later by cleanup.

## 10. Fetch/Open Behavior

When an admin opens a study whose local JTrack folder was already removed:

1. The backend looks up the latest synced `dataset_id` and dataset path from `study_activity`.
2. It clones/fetches from Juseless.
3. It restores the local JTrack folder.
4. The frontend shows loading while this first fetch happens.

This means first open can take a few seconds, but later opens are local again until cleanup removes the folder after sync.

## 11. Troubleshooting

### Password prompt appears in production

Production should not ask for passwords. Check:

```env
ECRF_JUSELESS_SSH_PASSWORD=
```

Then verify SSH key access:

```bash
ssh casee@juseless.inm7.de true
```

If this prompts for a password, SSH keys or account permissions are not ready.

### Sync fails with Permission denied

Example:

```text
Permission denied (publickey,password).
fatal: Could not read from remote repository.
```

Check:

- SSH username in `ECRF_DATALAD_SSH_REMOTE_TEMPLATE`
- SSH key installed for the backend OS user
- Juseless directory ownership/permissions
- whether the backend was restarted after `.env` changes

### Study stays local after logout

This is expected if:

- another session is active for that study
- sync is already running
- Juseless sync failed
- Juseless verification failed

Check DB:

```bash
sqlite3 /var/www/ecrf.inm7.de/www/casee/ecrf.db \
  "select id, study_id, state, last_sync_status, last_sync_at, last_error from study_activity order by id desc limit 20;"
```

`sync_failed` means local data was retained and will be retried.

### Sync already running

If a row is stuck in:

```text
state=syncing, last_sync_status=running
```

The backend recovery marks stale running syncs as failed after the stale timeout, so later cleanup can retry. Do not delete the local folder manually.

### Readable mirror missing but bare repo exists

The system treats mirror failure conservatively:

- bare repo may already have data
- local JTrack folder is retained
- sync is marked failed
- later retry should update the readable mirror

Check:

```env
ECRF_JUSELESS_MIRROR_AFTER_PUSH=1
ECRF_JUSELESS_STUDIES_DIR=/data/project/JTrack/CaseE/studies
```

## 12. Production Handover Checklist

Before handing hosting to another person:

- [ ] Production `.env` paths are updated.
- [ ] `ECRF_SECRET_KEY` is unique and strong.
- [ ] `ECRF_JUSELESS_SSH_PASSWORD` is empty.
- [ ] SSH key auth works non-interactively from JTrack to Juseless.
- [ ] Juseless bare repo root exists and is writable.
- [ ] Juseless readable studies root exists and is writable.
- [ ] `hosted/bin/python -m eCRF_backend.preflight` passes.
- [ ] One-study migration test succeeds.
- [ ] Readable mirror contains actual files.
- [ ] Full migration `--apply` succeeds.
- [ ] `--delete-local` is run only after verification.
- [ ] Daily cron/systemd sync is installed.
- [ ] Logs are checked after first daily run.
- [ ] Manual logout and auto logout sync are tested.
- [ ] Opening a removed local study fetches from Juseless successfully.
