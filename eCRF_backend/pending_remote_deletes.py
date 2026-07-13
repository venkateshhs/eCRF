from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from . import models
from .datalad_repo import DataladStudyRepo
from .logger import logger
from .utils import local_now


def _expected_dataset_name(dataset_path: str) -> str:
    return Path(dataset_path).expanduser().resolve().name


def enqueue_pending_remote_delete(
    db: Session,
    *,
    study_id: int,
    study_name: str,
    dataset_path: str,
    remote_url: str,
    last_error: Optional[str] = None,
) -> models.PendingRemoteDelete:
    remote_url = str(remote_url or "").strip()
    if not remote_url:
        raise ValueError("remote_url is required for pending remote delete")

    existing = (
        db.query(models.PendingRemoteDelete)
        .filter(
            models.PendingRemoteDelete.remote_url == remote_url,
            models.PendingRemoteDelete.status.in_(("pending", "failed")),
        )
        .order_by(models.PendingRemoteDelete.id.desc())
        .first()
    )
    if existing:
        existing.study_id = int(study_id)
        existing.study_name = study_name
        existing.dataset_path = dataset_path
        existing.status = "pending"
        existing.last_error = last_error
        db.flush()
        return existing

    row = models.PendingRemoteDelete(
        study_id=int(study_id),
        study_name=study_name,
        dataset_path=dataset_path,
        remote_url=remote_url,
        status="pending",
        attempts=0,
        last_error=last_error,
    )
    db.add(row)
    db.flush()
    return row


def retry_pending_remote_deletes(db: Session, *, limit: int = 20) -> int:
    stale_running_cutoff = local_now() - timedelta(minutes=30)
    stale_running_rows = (
        db.query(models.PendingRemoteDelete)
        .filter(
            models.PendingRemoteDelete.status == "running",
            models.PendingRemoteDelete.last_attempt_at < stale_running_cutoff,
        )
        .all()
    )
    for row in stale_running_rows:
        row.status = "failed"
        row.last_error = "Recovered stale pending remote delete retry after interruption."
    if stale_running_rows:
        db.commit()

    rows = (
        db.query(models.PendingRemoteDelete)
        .filter(models.PendingRemoteDelete.status.in_(("pending", "failed")))
        .order_by(models.PendingRemoteDelete.created_at.asc(), models.PendingRemoteDelete.id.asc())
        .limit(max(1, int(limit)))
        .all()
    )
    if not rows:
        return 0

    repo = DataladStudyRepo()
    completed = 0
    for row in rows:
        row.status = "running"
        row.attempts = int(row.attempts or 0) + 1
        row.last_attempt_at = local_now()
        db.commit()

        try:
            study_id = row.study_id
            remote_url = row.remote_url
            repo.delete_remote_bare_repo_url(
                row.remote_url,
                expected_dataset_name=_expected_dataset_name(row.dataset_path),
            )
            repo.delete_remote_worktree_for_dataset(Path(row.dataset_path))
            db.delete(row)
            db.commit()
            completed += 1
            logger.info(
                "Completed pending Juseless delete for study_id=%s remote=%s",
                study_id,
                remote_url,
            )
        except Exception as e:
            db.rollback()
            row = db.query(models.PendingRemoteDelete).filter(models.PendingRemoteDelete.id == row.id).first()
            if row:
                row.status = "failed"
                row.last_attempt_at = local_now()
                row.last_error = str(e)
                db.commit()
            logger.warning(
                "Pending Juseless delete retry failed for study_id=%s remote=%s: %s",
                getattr(row, "study_id", None),
                getattr(row, "remote_url", None),
                e,
            )
    return completed
