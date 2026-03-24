# scripts/migrate_sql_to_datalad.py
from __future__ import annotations

import argparse
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from eCRF_backend.database import SessionLocal
from eCRF_backend import models
from eCRF_backend.datalad_config import get_datalad_config
from eCRF_backend.datalad_store import DataladStudyStore

try:
    from datalad.api import Dataset  # type: ignore
except Exception:
    Dataset = None  # type: ignore


def _iso(dt) -> str:
    if not dt:
        return ""
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    return str(dt)


def _git_commit_with_date(ds_path: Path, message: str, when_iso: str) -> None:
    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = when_iso
    env["GIT_COMMITTER_DATE"] = when_iso
    subprocess.run(["git", "-C", str(ds_path), "add", "-A"], check=True, env=env)
    # allow empty commits so timestamps match audit trail even if payload duplicates
    subprocess.run(["git", "-C", str(ds_path), "commit", "--allow-empty", "-m", message], check=True, env=env)


def migrate(dry_run: bool, commit_per_event: bool) -> None:
    cfg = get_datalad_config()
    store = DataladStudyStore(cfg, worker=None)

    db = SessionLocal()
    try:
        studies = db.query(models.StudyMetadata).order_by(models.StudyMetadata.id.asc()).all()
        print(f"Found {len(studies)} studies")
        for meta in studies:
            content = db.query(models.StudyContent).filter_by(study_id=meta.id).first()
            study_data = (content.study_data or {}) if content and isinstance(content.study_data, dict) else {}

            print(f"Study {meta.id}: {meta.study_name} status={getattr(meta, 'status', None)}")
            if dry_run:
                continue

            refs = store.write_study_snapshot(db, meta.id)

            if Dataset is None:
                raise RuntimeError("DataLad not installed")

            # One bootstrap save commit for full snapshot
            Dataset(str(refs.dataset_path)).save(message=f"bootstrap: import SQL snapshot (study {meta.id})")

            if commit_per_event:
                # Replay audit events into git history as additional commits
                events = (
                    db.query(models.AuditEvent)
                    .filter(models.AuditEvent.study_id == meta.id)
                    .order_by(models.AuditEvent.timestamp.asc())
                    .all()
                )
                audit_dir = refs.dataset_path / "canonical" / "audit_events"
                audit_dir.mkdir(parents=True, exist_ok=True)

                for ev in events:
                    # Store event envelope file (idempotent naming by id)
                    p = audit_dir / f"event_{int(ev.id):09d}.json"
                    p.write_text(
                        __import__("json").dumps(
                            {
                                "id": ev.id,
                                "timestamp": _iso(ev.timestamp),
                                "study_id": ev.study_id,
                                "subject_id": ev.subject_id,
                                "user_id": ev.user_id,
                                "action": ev.action,
                                "details": ev.details,
                            },
                            ensure_ascii=False,
                            indent=2,
                        ),
                        encoding="utf-8",
                    )
                    when = _iso(ev.timestamp) or datetime.now(timezone.utc).isoformat()
                    _git_commit_with_date(
                        refs.dataset_path,
                        message=f"audit:{ev.action} event={ev.id} study={meta.id}",
                        when_iso=when,
                    )

    finally:
        db.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Print what would happen without modifying anything")
    ap.add_argument("--apply", action="store_true", help="Apply migration (write files and commits)")
    ap.add_argument("--commit-per-event", action="store_true", help="Replay SQL audit events as git commits")
    args = ap.parse_args()

    if args.dry_run and args.apply:
        raise SystemExit("Choose one of --dry-run or --apply")

    migrate(dry_run=(not args.apply), commit_per_event=args.commit_per_event)


if __name__ == "__main__":
    main()
