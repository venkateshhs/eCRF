from __future__ import annotations

import shutil
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Set

from sqlalchemy.orm import Session

from . import models
from .datalad_repo import DataladStudyRepo
from .logger import logger
from .utils import local_now


ACTIVE_STATES = {"active", "syncing"}
SYNC_CANDIDATE_STATES = {"released", "sync_failed"}
LOCAL_ONLY_STATES = {"view_expired"}
STALE_SYNC_MINUTES = 30


def _to_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is not None and dt.utcoffset() is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _to_naive_local(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is not None and dt.utcoffset() is not None:
        return dt.astimezone().replace(tzinfo=None)
    return dt


def _inactivity_minutes() -> int:
    try:
        return max(1, int(os.getenv("ECRF_SESSION_INACTIVITY_MINUTES", "30")))
    except Exception:
        return 30


def _shared_view_ttl_minutes() -> int:
    try:
        return max(1, int(os.getenv("ECRF_SHARED_LINK_VIEW_TTL_MINUTES", "120")))
    except Exception:
        return 120


def record_study_activity(
    db: Session,
    *,
    study_id: int,
    dataset_path: Path,
    user_id: Optional[int],
    session_jti: Optional[str],
    purpose: str = "create_study",
    metadata: Optional[Dict[str, Any]] = None,
) -> models.StudyActivity:
    now = local_now()
    if session_jti:
        existing = (
            db.query(models.StudyActivity)
            .filter(
                models.StudyActivity.study_id == int(study_id),
                models.StudyActivity.user_id == user_id,
                models.StudyActivity.session_jti == session_jti,
                models.StudyActivity.state == "active",
            )
            .first()
        )
        if existing:
            existing.dataset_path = str(Path(dataset_path).expanduser().resolve())
            existing.last_seen_at = now
            existing.purpose = purpose or existing.purpose
            if metadata:
                merged = dict(existing.metadata_json or {})
                merged.update(metadata)
                existing.metadata_json = merged
            db.commit()
            db.refresh(existing)
            return existing

    row = models.StudyActivity(
        study_id=int(study_id),
        dataset_path=str(Path(dataset_path).expanduser().resolve()),
        user_id=user_id,
        session_jti=session_jti,
        state="active",
        purpose=purpose,
        acquired_at=now,
        last_seen_at=now,
        metadata_json=metadata or {},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _safe_remove_local_dataset(dataset_path: Path, *, study_id: Optional[int] = None) -> None:
    repo = DataladStudyRepo()
    dataset_path = Path(dataset_path).expanduser().resolve()
    root = repo.root.resolve()
    if dataset_path == root or root not in dataset_path.parents:
        raise RuntimeError(f"Refusing to remove dataset outside BIDS_ROOT: {dataset_path}")
    if not dataset_path.name.startswith("study_"):
        raise RuntimeError(f"Refusing to remove non-study dataset path: {dataset_path}")
    if study_id is not None and not dataset_path.name.startswith(f"study_{int(study_id)}_"):
        raise RuntimeError(f"Refusing to remove dataset with unexpected study id prefix: {dataset_path}")
    if dataset_path.exists() and not (dataset_path / ".git").exists() and not (dataset_path / ".datalad").exists():
        raise RuntimeError(f"Refusing to remove non-DataLad study folder: {dataset_path}")
    if dataset_path.exists():
        shutil.rmtree(dataset_path)


def _activity_dataset_id(row: models.StudyActivity) -> Optional[str]:
    metadata = row.metadata_json or {}
    if isinstance(metadata, dict) and metadata.get("dataset_id"):
        return str(metadata["dataset_id"])
    return None


def _mark_sync_row_local_removed(db: Session, row: models.StudyActivity, *, reason: str) -> None:
    row.state = "local_removed"
    row.last_sync_status = "synced_local_removed"
    row.last_sync_at = local_now()
    row.last_error = reason
    db.commit()


def _mark_sync_row_failed(db: Session, row: models.StudyActivity, *, error: str) -> None:
    row.state = "sync_failed"
    row.last_sync_status = "failed"
    row.last_sync_at = local_now()
    row.last_error = error
    db.commit()


def _sync_activity_row(db: Session, row: models.StudyActivity) -> bool:
    row_id = row.id
    now = local_now()
    dataset_path = Path(row.dataset_path).expanduser().resolve()

    if not dataset_path.exists():
        if _activity_dataset_id(row):
            _mark_sync_row_local_removed(
                db,
                row,
                reason="Local dataset already absent; Juseless dataset id is recorded.",
            )
            logger.info(
                "Skipping sync for study_id=%s because local dataset is already absent and dataset_id is recorded: %s",
                row.study_id,
                dataset_path,
            )
            return True

        _mark_sync_row_failed(
            db,
            row,
            error=f"Local dataset is missing and no Juseless dataset id is recorded: {dataset_path}",
        )
        logger.warning(
            "Skipping sync for study_id=%s because local dataset is missing and no dataset_id is recorded: %s",
            row.study_id,
            dataset_path,
        )
        return False

    if not dataset_path.is_dir() or not (dataset_path / ".git").exists() and not (dataset_path / ".datalad").exists():
        _mark_sync_row_failed(
            db,
            row,
            error=f"Local dataset path is not an installed DataLad dataset: {dataset_path}",
        )
        logger.warning(
            "Skipping sync for study_id=%s because local dataset path is not a DataLad dataset: %s",
            row.study_id,
            dataset_path,
        )
        return False

    row.state = "syncing"
    row.last_sync_status = "running"
    row.last_sync_at = now
    row.last_error = None
    db.commit()

    try:
        repo = DataladStudyRepo()
        dataset_id = repo.sync_to_remote(
            dataset_path,
            f"case-e: logout sync study={row.study_id}",
        )
        if not dataset_id:
            raise RuntimeError(
                f"DataLad sync completed for study_id={row.study_id} but dataset id was not available; "
                "local dataset will not be removed."
            )
        metadata = dict(row.metadata_json or {})
        metadata["dataset_id"] = dataset_id
        row.metadata_json = metadata
        row.state = "synced"
        row.last_sync_status = "synced"
        row.last_sync_at = local_now()
        row.last_error = None
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        row = db.query(models.StudyActivity).filter(models.StudyActivity.id == row_id).first()
        if row:
            row.state = "sync_failed"
            row.last_sync_status = "failed"
            row.last_sync_at = local_now()
            row.last_error = str(e)
            db.commit()
        logger.exception(
            "Study logout sync failed for study_id=%s dataset=%s",
            row.study_id if row else None,
            row.dataset_path if row else None,
        )
        return False


def _mark_inactive_session_rows_released(db: Session, reason: str) -> Set[int]:
    rows = (
        db.query(models.StudyActivity)
        .join(
            models.UserSession,
            models.UserSession.jti == models.StudyActivity.session_jti,
        )
        .filter(
            models.StudyActivity.state == "active",
        )
        .all()
    )
    if not rows:
        return set()

    now = local_now()
    now_cmp = _to_naive_local(now) or datetime.now()
    inactivity_cutoff = now_cmp - timedelta(minutes=_inactivity_minutes())
    affected_study_ids: Set[int] = set()
    for row in rows:
        session = row.session_jti and getattr(row, "session", None)
        session = session or (
            db.query(models.UserSession)
            .filter(models.UserSession.jti == row.session_jti)
            .first()
        )
        if not session:
            continue

        revoked = session.revoked_at is not None
        absolute_expired = bool(
            _to_naive_local(session.absolute_expires_at)
            and _to_naive_local(session.absolute_expires_at) < now_cmp
        )
        inactive = bool(
            _to_naive_local(session.last_activity_at)
            and _to_naive_local(session.last_activity_at) < inactivity_cutoff
        )
        if not (revoked or absolute_expired or inactive):
            continue

        if not revoked:
            session.revoked_at = now
        row.state = "released"
        row.released_at = now
        row.release_reason = (
            "session_revoked" if revoked else "session_expired" if absolute_expired else "session_inactive"
        )
        row.last_seen_at = now
        affected_study_ids.add(int(row.study_id))
    if affected_study_ids:
        db.commit()
    return affected_study_ids


def _recover_stale_syncing_rows(db: Session) -> Set[int]:
    now = local_now()
    cutoff = (_to_naive_local(now) or datetime.now()) - timedelta(minutes=STALE_SYNC_MINUTES)
    rows = (
        db.query(models.StudyActivity)
        .filter(
            models.StudyActivity.state == "syncing",
            models.StudyActivity.last_sync_status == "running",
        )
        .all()
    )
    affected_study_ids: Set[int] = set()
    for row in rows:
        last_sync_at = _to_naive_local(row.last_sync_at)
        if last_sync_at and last_sync_at >= cutoff:
            continue
        row.state = "sync_failed"
        row.last_sync_status = "failed"
        row.last_error = "Recovered stale running sync after backend restart or interrupted sync."
        row.last_sync_at = now
        affected_study_ids.add(int(row.study_id))
    if affected_study_ids:
        db.commit()
    return affected_study_ids


def _active_count_for_study(db: Session, study_id: int) -> int:
    return (
        db.query(models.StudyActivity)
        .filter(
            models.StudyActivity.study_id == int(study_id),
            models.StudyActivity.state.in_(ACTIVE_STATES),
        )
        .count()
    )


def _active_states_for_study(db: Session, study_id: int) -> Set[str]:
    return {
        str(row[0])
        for row in (
            db.query(models.StudyActivity.state)
            .filter(
                models.StudyActivity.study_id == int(study_id),
                models.StudyActivity.state.in_(ACTIVE_STATES),
            )
            .distinct()
            .all()
        )
    }


def _sync_candidate_count_for_study(db: Session, study_id: int) -> int:
    return (
        db.query(models.StudyActivity)
        .filter(
            models.StudyActivity.study_id == int(study_id),
            models.StudyActivity.state.in_(SYNC_CANDIDATE_STATES | {"syncing"}),
        )
        .count()
    )


def _remove_local_only_study_if_unused(db: Session, study_id: int) -> None:
    if _active_count_for_study(db, study_id) or _sync_candidate_count_for_study(db, study_id):
        return

    row = (
        db.query(models.StudyActivity)
        .filter(
            models.StudyActivity.study_id == int(study_id),
            models.StudyActivity.state.in_(LOCAL_ONLY_STATES | {"local_removed"}),
        )
        .order_by(models.StudyActivity.last_seen_at.desc(), models.StudyActivity.id.desc())
        .first()
    )
    if not row:
        return

    dataset_path = Path(row.dataset_path)
    try:
        _safe_remove_local_dataset(dataset_path, study_id=study_id)
        now = local_now()
        rows_to_close = (
            db.query(models.StudyActivity)
            .filter(
                models.StudyActivity.study_id == int(study_id),
                models.StudyActivity.state.in_(LOCAL_ONLY_STATES),
            )
            .all()
        )
        for item in rows_to_close:
            item.state = "local_removed"
            item.last_sync_status = "local_only_removed"
            item.last_sync_at = now
            item.last_error = None
        db.commit()
        logger.info(
            "Removed local-only JTrack dataset for study_id=%s dataset=%s",
            study_id,
            dataset_path,
        )
    except Exception as e:
        db.rollback()
        row = db.query(models.StudyActivity).filter(models.StudyActivity.id == row.id).first()
        if row:
            row.last_sync_status = "local_only_remove_failed"
            row.last_error = str(e)
            db.commit()
        logger.exception(
            "Failed to remove local-only JTrack dataset for study_id=%s dataset=%s",
            study_id,
            dataset_path,
        )


def cleanup_stale_shared_views(db: Session) -> None:
    cutoff = local_now() - timedelta(minutes=_shared_view_ttl_minutes())
    rows = (
        db.query(models.StudyActivity)
        .filter(
            models.StudyActivity.state == "active",
            models.StudyActivity.purpose == "shared_link_view",
            models.StudyActivity.last_seen_at < cutoff,
        )
        .all()
    )
    if not rows:
        return

    now = local_now()
    study_ids: Set[int] = set()
    for row in rows:
        row.state = "released"
        row.released_at = now
        row.release_reason = "shared_link_view_timeout"
        row.last_seen_at = now
        study_ids.add(int(row.study_id))
    db.commit()

    sync_and_remove_unaccessed_studies(db, reason="shared_link_view_timeout")


def release_activity_by_session(
    db: Session,
    *,
    session_jti: str,
    reason: str,
    sync_after_release: bool = True,
) -> None:
    rows = (
        db.query(models.StudyActivity)
        .filter(
            models.StudyActivity.session_jti == session_jti,
            models.StudyActivity.state == "active",
        )
        .all()
    )
    if not rows:
        if sync_after_release:
            sync_and_remove_unaccessed_studies(db, reason=reason)
        return

    now = local_now()
    study_ids: Set[int] = set()
    for row in rows:
        row.state = "released" if sync_after_release else "view_expired"
        row.released_at = now
        row.release_reason = reason
        row.last_seen_at = now
        study_ids.add(int(row.study_id))
    db.commit()

    if sync_after_release:
        sync_and_remove_unaccessed_studies(db, reason=reason)
    else:
        for study_id in sorted(study_ids):
            _remove_local_only_study_if_unused(db, study_id)


def expire_shared_view_for_token(db: Session, *, token: str) -> None:
    release_activity_by_session(
        db,
        session_jti=f"shared-view:{token}",
        reason="shared_link_submit_started",
        sync_after_release=True,
    )


def sync_and_remove_unaccessed_studies(db: Session, *, reason: str = "logout") -> None:
    cleanup_stale_shared_views(db) if reason != "shared_link_view_timeout" else None
    _mark_inactive_session_rows_released(db, reason)
    _recover_stale_syncing_rows(db)
    try:
        from .pending_remote_deletes import retry_pending_remote_deletes

        retry_pending_remote_deletes(db)
    except Exception:
        logger.exception("Pending Juseless delete retry failed during study cleanup")

    study_ids = {
        int(row[0])
        for row in (
            db.query(models.StudyActivity.study_id)
            .filter(models.StudyActivity.state.in_(SYNC_CANDIDATE_STATES))
            .distinct()
            .all()
        )
    }

    for study_id in sorted(study_ids):
        active_states = _active_states_for_study(db, study_id)
        if active_states:
            if "syncing" in active_states:
                logger.info(
                    "Skipping logout cleanup for study_id=%s because sync is already running",
                    study_id,
                )
            else:
                logger.info(
                    "Skipping logout cleanup for study_id=%s because another session is active",
                    study_id,
                )
            continue

        row_to_sync = (
            db.query(models.StudyActivity)
            .filter(
                models.StudyActivity.study_id == study_id,
                models.StudyActivity.state.in_(SYNC_CANDIDATE_STATES),
            )
            .order_by(models.StudyActivity.last_seen_at.desc(), models.StudyActivity.id.desc())
            .first()
        )
        if not row_to_sync:
            continue

        if _sync_activity_row(db, row_to_sync):
            dataset_path = Path(row_to_sync.dataset_path)
            try:
                _safe_remove_local_dataset(dataset_path, study_id=study_id)
                cleanup_time = local_now()
                rows_to_close = (
                    db.query(models.StudyActivity)
                    .filter(
                        models.StudyActivity.study_id == study_id,
                        models.StudyActivity.state.in_(SYNC_CANDIDATE_STATES | {"synced"}),
                    )
                    .all()
                )
                metadata = dict(row_to_sync.metadata_json or {})
                for row in rows_to_close:
                    row.state = "local_removed"
                    row.last_sync_status = "synced_local_removed"
                    row.last_sync_at = cleanup_time
                    row.last_error = None
                    if metadata:
                        row_metadata = dict(row.metadata_json or {})
                        row_metadata.update(metadata)
                        row.metadata_json = row_metadata
                db.commit()
                logger.info(
                    "Synced and removed local JTrack dataset for study_id=%s dataset=%s",
                    study_id,
                    dataset_path,
                )
            except Exception as e:
                db.rollback()
                row_to_sync = (
                    db.query(models.StudyActivity)
                    .filter(models.StudyActivity.id == row_to_sync.id)
                    .first()
                )
                if row_to_sync:
                    row_to_sync.state = "synced"
                    row_to_sync.last_sync_status = "synced_remove_failed"
                    row_to_sync.last_error = str(e)
                    db.commit()
                logger.exception(
                    "Study synced but local removal failed for study_id=%s dataset=%s",
                    study_id,
                    dataset_path,
                )


def release_session_study_activities(
    db: Session,
    *,
    user_id: int,
    session_jti: Optional[str],
    reason: str = "logout",
) -> None:
    if not session_jti:
        return

    rows = (
        db.query(models.StudyActivity)
        .filter(
            models.StudyActivity.user_id == int(user_id),
            models.StudyActivity.session_jti == session_jti,
            models.StudyActivity.state == "active",
        )
        .all()
    )
    if not rows:
        sync_and_remove_unaccessed_studies(db, reason=reason)
        return

    now = local_now()
    for row in rows:
        row.state = "released"
        row.released_at = now
        row.release_reason = reason
        row.last_seen_at = now
    db.commit()

    sync_and_remove_unaccessed_studies(db, reason=reason)
