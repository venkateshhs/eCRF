# eCRF_backend/datalad_hooks.py
from __future__ import annotations

from typing import Optional
from sqlalchemy.orm import Session

from .datalad_runtime import get_datalad_store
from .logger import logger


def snapshot_study_after_change(
    db: Session,
    study_id: int,
    action: str,
    entry_id: Optional[int] = None,
) -> None:
    store = get_datalad_store()
    if store is None:
        return

    try:
        refs = store.write_study_snapshot(db, study_id)

        if entry_id is not None:
            try:
                store.write_entry_snapshot(db, entry_id)
            except Exception as e:
                logger.error(
                    "DataLad entry snapshot failed for study_id=%s entry_id=%s: %s",
                    study_id, entry_id, e
                )

        msg = f"case-e: {action} study={study_id}"
        if entry_id is not None:
            msg += f" entry={entry_id}"

        store.schedule_save(refs, msg)
    except Exception as e:
        logger.error(
            "DataLad study snapshot failed for study_id=%s action=%s: %s",
            study_id, action, e
        )