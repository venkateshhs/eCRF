# eCRF_backend/datalad_patch.py
from __future__ import annotations

from typing import Any, Dict, Optional

from .datalad_config import get_datalad_config, is_datalad_enabled
from .datalad_store import DataladStudyStore
from .datalad_worker import DataladWorker

from .logger import logger

# Import the existing module we will wrap
from . import bids_exporter as be  # type: ignore


def install_datalad_audit_hooks(store: DataladStudyStore) -> None:
    """
    Monkeypatch bids_exporter audit functions to also write canonical snapshots.
    This avoids editing existing router files while capturing core mutations.
    """

    orig_audit_change_both = be.audit_change_both
    orig_audit_access_change_both = getattr(be, "audit_access_change_both", None)

    def wrapped_audit_change_both(
        *,
        scope: Optional[str] = None,
        action: str,
        actor: Optional[str] = None,
        study_id: Optional[int] = None,
        study_name: Optional[str] = None,
        subject_index: Optional[int] = None,
        visit_index: Optional[int] = None,
        extra: Optional[Dict[str, Any]] = None,
        db=None,
        actor_id: Optional[int] = None,
        actor_name: Optional[str] = None,
        detail: Optional[Dict[str, Any]] = None,
    ) -> None:
        # Preserve current behaviour first
        orig_audit_change_both(
            scope=scope,
            action=action,
            actor=actor,
            study_id=study_id,
            study_name=study_name,
            subject_index=subject_index,
            visit_index=visit_index,
            extra=extra,
            db=db,
            actor_id=actor_id,
            actor_name=actor_name,
            detail=detail,
        )

        cfg = store.cfg
        if not is_datalad_enabled(cfg):
            return
        if db is None or study_id is None:
            return

        try:
            refs = store.write_study_snapshot(db, int(study_id))
            msg = f"case-e: {action} study={study_id} actor={actor_id or ''}"
            store.schedule_save(refs, msg)
        except Exception as e:
            logger.error("DataLad snapshot failed for study action=%s study_id=%s: %s", action, study_id, e)

        # If this action references an entry, persist the canonical entry snapshot too
        try:
            if extra and "entry_id" in extra:
                entry_id = int(extra["entry_id"])
                s_id, _ = store.write_entry_snapshot(db, entry_id)
                # schedule a save message; already queued above, but extra save is safe
                refs2 = store.write_study_snapshot(db, s_id)
                store.schedule_save(refs2, f"case-e: {action} entry={entry_id} study={s_id}")
        except Exception:
            # best effort
            pass

    def wrapped_audit_access_change_both(*args, **kwargs):
        if orig_audit_access_change_both is None:
            return
        orig_audit_access_change_both(*args, **kwargs)
        cfg = store.cfg
        if not is_datalad_enabled(cfg):
            return

        # access audit helper in case-e passes study_id/study_name in kwargs
        db = kwargs.get("db", None)
        study_id = kwargs.get("study_id", None)
        if db is None or study_id is None:
            return
        try:
            refs = store.write_study_snapshot(db, int(study_id))
            store.schedule_save(refs, f"case-e: access_change study={study_id}")
        except Exception as e:
            logger.error("DataLad snapshot failed for access_change study_id=%s: %s", study_id, e)

    be.audit_change_both = wrapped_audit_change_both
    if orig_audit_access_change_both is not None:
        be.audit_access_change_both = wrapped_audit_access_change_both
