from __future__ import annotations

# One-time production migration for old JTrack study folders that do not yet
# have study_activity rows and have not been synced to Juseless.
#
# Safety principles:
#   - Dry-run is the default.
#   - Missing or ambiguous study folders are skipped, not guessed.
#   - Each study is saved, pushed to Juseless, verified, mirrored into the
#     readable Juseless studies directory, and then recorded in study_activity.
#   - Local JTrack study folders are deleted only when --delete-local is passed,
#     and only after successful sync/verification/activity update.
#   - Local deletion is skipped when a study has active/syncing activity rows.
#   - If one study fails, the script reports the error and continues with the
#     next study. Local JTrack data is retained.
#
# Safe production runbook:
#   1. Put the site in maintenance mode so no user can edit data during migration.
#   2. Back up the database, for example:
#        cp ecrf.db ecrf.db.before-juseless-migration
#   3. Make sure the JTrack bids_datasets directory is backed up or snapshotted.
#   4. Run a dry-run and inspect candidate/skipped/orphan/ambiguous output:
#        hosted/bin/python -m eCRF_backend.scripts.sync_jtrack_to_juseless
#   5. Apply to one study first:
#        hosted/bin/python -m eCRF_backend.scripts.sync_jtrack_to_juseless --apply --study-id 7
#   6. Verify on Juseless:
#        - bare repo exists under .../bids_datasets/study_<id>_....git
#        - readable mirror exists under .../studies/study_<id>_...
#        - files are visible in the readable mirror
#   7. Apply to all published studies without deleting local JTrack folders:
#        hosted/bin/python -m eCRF_backend.scripts.sync_jtrack_to_juseless --apply
#   8. For daily cleanup, delete local JTrack folders only after verified sync:
#        hosted/bin/python -m eCRF_backend.scripts.sync_jtrack_to_juseless --apply --delete-local
#
# Usage from the repository root:
#
#   hosted/bin/python -m eCRF_backend.scripts.sync_jtrack_to_juseless
#
# Dry-run is the default. It prints what would be migrated without changing
# Juseless or the database.
#
# Apply migration for all published studies:
#
#   hosted/bin/python -m eCRF_backend.scripts.sync_jtrack_to_juseless --apply
#
# Apply migration for one study:
#
#   hosted/bin/python -m eCRF_backend.scripts.sync_jtrack_to_juseless --apply --study-id 12
#
# Safer production rollout:
#   1. Run without flags and inspect the dry-run output.
#   2. Run with --apply.
#   3. Verify clone/open behavior from Juseless for selected studies.
#
# This script is local-retaining unless --delete-local is passed. Do not use
# --delete-local during the initial production migration until a non-deleting
# apply run has been verified.

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import Iterable, Optional


def _load_dotenv() -> None:
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        return

    loaded: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and ((value[0] == value[-1] == '"') or (value[0] == value[-1] == "'")):
            value = value[1:-1]
        if key:
            loaded[key] = value

    for key, value in loaded.items():
        os.environ.setdefault(key, value)


def _ensure_import_path() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


_load_dotenv()
_ensure_import_path()

from sqlalchemy.orm import Session  # noqa: E402

from eCRF_backend import models  # noqa: E402
from eCRF_backend.database import Base, SessionLocal, engine  # noqa: E402
from eCRF_backend.datalad_repo import DataladStudyRepo  # noqa: E402
from eCRF_backend.utils import local_now  # noqa: E402


def _published_status(value: Optional[str]) -> bool:
    return (value or "PUBLISHED").strip().upper() == "PUBLISHED"


def _candidate_studies(db: Session, study_ids: Optional[set[int]]) -> Iterable[models.StudyMetadata]:
    query = db.query(models.StudyMetadata).order_by(models.StudyMetadata.id.asc())
    if study_ids:
        query = query.filter(models.StudyMetadata.id.in_(study_ids))
    for meta in query.all():
        if _published_status(getattr(meta, "status", None)):
            yield meta


def _dataset_id_from_folder_name(path: Path) -> Optional[int]:
    name = path.name
    if not name.startswith("study_"):
        return None
    rest = name[len("study_"):]
    first_part = rest.split("_", 1)[0]
    if not first_part.isdigit():
        return None
    return int(first_part)


def _resolve_dataset_path(repo: DataladStudyRepo, meta: models.StudyMetadata) -> tuple[Optional[Path], str]:
    expected = repo.paths(meta.id, meta.study_name).dataset_path
    if expected.exists():
        return expected, "expected"

    matches = sorted(repo.root.glob(f"study_{int(meta.id)}_*"))
    matches = [p for p in matches if p.is_dir()]
    if not matches:
        return None, "missing"
    if len(matches) == 1:
        return matches[0].resolve(), "fallback_by_study_id"

    return None, "ambiguous:" + ", ".join(str(p) for p in matches)


def _active_activity_count(db: Session, study_id: int) -> int:
    return (
        db.query(models.StudyActivity)
        .filter(
            models.StudyActivity.study_id == int(study_id),
            models.StudyActivity.state.in_(("active", "syncing")),
        )
        .count()
    )


def _safe_remove_dataset(repo: DataladStudyRepo, dataset_path: Path, *, study_id: int) -> None:
    dataset_path = Path(dataset_path).expanduser().resolve()
    root = repo.root.resolve()
    if dataset_path == root or root not in dataset_path.parents:
        raise RuntimeError(f"Refusing to remove dataset outside BIDS_ROOT: {dataset_path}")
    if not dataset_path.name.startswith(f"study_{int(study_id)}_"):
        raise RuntimeError(
            f"Refusing to remove dataset with unexpected study id prefix: {dataset_path}"
        )
    if dataset_path.exists() and not (dataset_path / ".git").exists() and not (dataset_path / ".datalad").exists():
        raise RuntimeError(f"Refusing to remove non-DataLad study folder: {dataset_path}")
    if dataset_path.exists():
        shutil.rmtree(dataset_path)


def _report_orphan_folders(repo: DataladStudyRepo, db: Session) -> None:
    known_ids = {
        int(row[0])
        for row in db.query(models.StudyMetadata.id).all()
        if row and row[0] is not None
    }
    orphan_paths = []
    for path in sorted(repo.root.glob("study_*")):
        if not path.is_dir():
            continue
        study_id = _dataset_id_from_folder_name(path)
        if study_id is not None and study_id not in known_ids:
            orphan_paths.append(path)

    if not orphan_paths:
        return

    print("\nWARNING: Found local JTrack study folders without matching StudyMetadata rows.")
    print("These are not migrated because the backend cannot safely attach them to a study.")
    for path in orphan_paths:
        print(f"  ORPHAN: {path}")


def _upsert_activity(
    db: Session,
    *,
    meta: models.StudyMetadata,
    dataset_path: Path,
    dataset_id: str,
) -> models.StudyActivity:
    now = local_now()
    metadata = {
        "study_name": meta.study_name,
        "dataset_id": dataset_id,
        "migration": "sync_jtrack_to_juseless",
    }
    row = (
        db.query(models.StudyActivity)
        .filter(
            models.StudyActivity.study_id == int(meta.id),
            models.StudyActivity.purpose == "migration_sync",
        )
        .order_by(models.StudyActivity.id.desc())
        .first()
    )
    if row is None:
        row = models.StudyActivity(
            study_id=int(meta.id),
            dataset_path=str(Path(dataset_path).expanduser().resolve()),
            user_id=None,
            session_jti=f"migration:study:{int(meta.id)}",
            purpose="migration_sync",
            acquired_at=now,
            last_seen_at=now,
        )
        db.add(row)

    row.dataset_path = str(Path(dataset_path).expanduser().resolve())
    row.state = "synced"
    row.released_at = now
    row.release_reason = "migration_sync"
    row.last_seen_at = now
    row.last_sync_status = "synced"
    row.last_sync_at = now
    row.last_error = None
    row.metadata_json = metadata
    db.commit()
    db.refresh(row)
    return row


def _mark_activity_local_removed(db: Session, *, row: models.StudyActivity) -> None:
    row.state = "local_removed"
    row.last_sync_status = "synced_local_removed"
    row.last_sync_at = local_now()
    row.last_error = None
    db.commit()


def sync_studies(*, apply: bool, delete_local: bool, study_ids: Optional[set[int]]) -> int:
    Base.metadata.create_all(bind=engine)

    repo = DataladStudyRepo()
    db = SessionLocal()
    failures: list[tuple[int, str]] = []
    synced = 0
    skipped = 0

    try:
        candidates = list(_candidate_studies(db, study_ids))
        print(f"Found {len(candidates)} published study candidate(s).")
        _report_orphan_folders(repo, db)
        for meta in candidates:
            dataset_path, source = _resolve_dataset_path(repo, meta)
            print(f"\nStudy {meta.id}: {meta.study_name}")
            print(f"  expected dataset: {repo.paths(meta.id, meta.study_name).dataset_path}")
            print(f"  resolved dataset: {dataset_path or '(none)'}")
            print(f"  resolution: {source}")

            if dataset_path is None or not dataset_path.exists():
                message = "local JTrack dataset folder is missing or ambiguous; cannot migrate safely"
                print(f"  SKIP: {message}")
                skipped += 1
                continue

            if not apply:
                if delete_local:
                    print("  DRY-RUN: would save, push, verify, write dataset_id, then delete local JTrack folder")
                else:
                    print("  DRY-RUN: would save, push, verify, and write dataset_id to study_activity")
                continue

            try:
                dataset_id = repo.sync_to_remote(
                    dataset_path,
                    f"case-e: initial JTrack to Juseless sync study={meta.id}",
                )
                if not dataset_id:
                    raise RuntimeError("sync completed but DataLad dataset id was not available")

                row = _upsert_activity(
                    db,
                    meta=meta,
                    dataset_path=dataset_path,
                    dataset_id=str(dataset_id),
                )
                synced += 1
                print(f"  OK: synced dataset_id={dataset_id}")

                if delete_local:
                    active_count = _active_activity_count(db, int(meta.id))
                    if active_count:
                        print(
                            "  SKIP LOCAL DELETE: "
                            f"{active_count} active/syncing activity row(s) exist for this study"
                        )
                    elif source != "expected":
                        print(
                            "  SKIP LOCAL DELETE: resolved folder did not match expected DB-derived folder name; "
                            "sync completed but local folder is retained for manual review"
                        )
                    else:
                        _safe_remove_dataset(repo, dataset_path, study_id=int(meta.id))
                        _mark_activity_local_removed(db, row=row)
                        print("  OK: local JTrack dataset removed after verified sync")
            except Exception as exc:
                db.rollback()
                failures.append((int(meta.id), str(exc)))
                print(f"  ERROR: {exc}")

        print("\nSummary")
        print(f"  synced:  {synced}")
        print(f"  skipped: {skipped}")
        print(f"  failed:  {len(failures)}")
        for study_id, error in failures:
            print(f"  - study {study_id}: {error}")

        return 1 if failures else 0
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="One-time migration/sync of published JTrack study datasets to Juseless."
    )
    parser.add_argument("--apply", action="store_true", help="Actually sync to Juseless and update DB.")
    parser.add_argument(
        "--delete-local",
        action="store_true",
        help="After successful verified sync and DB update, remove the local JTrack study folder.",
    )
    parser.add_argument(
        "--study-id",
        type=int,
        action="append",
        help="Only sync a specific study id. Can be passed multiple times.",
    )
    args = parser.parse_args()

    raise SystemExit(
        sync_studies(
            apply=bool(args.apply),
            delete_local=bool(args.delete_local),
            study_ids=set(args.study_id or []) or None,
        )
    )


if __name__ == "__main__":
    main()
