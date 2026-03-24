# eCRF_backend/datalad_runtime.py
from __future__ import annotations

from typing import Optional

from .datalad_config import get_datalad_config, is_datalad_enabled
from .datalad_store import DataladStudyStore
from .datalad_worker import DataladWorker
from .logger import logger

_worker: Optional[DataladWorker] = None
_store: Optional[DataladStudyStore] = None


def init_datalad_runtime() -> None:
    global _worker, _store

    if _store is not None:
        return

    cfg = get_datalad_config()
    if not is_datalad_enabled(cfg):
        logger.info("DataLad runtime disabled")
        return

    _worker = DataladWorker(cfg, log=lambda s: logger.info(s))
    _worker.start()
    _store = DataladStudyStore(cfg, worker=_worker)
    logger.info("DataLad runtime initialized")


def shutdown_datalad_runtime() -> None:
    global _worker
    if _worker is not None:
        _worker.stop()


def get_datalad_store() -> Optional[DataladStudyStore]:
    return _store